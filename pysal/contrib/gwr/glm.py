#TODO
# Documentation for y_fix
# Add model diagnostics as cached properties:
# Add family class functionality so that diagnostics are methods of family class
# intead of using different cases for family for each diagnostic.

import numpy as np
import numpy.linalg as la
from pysal.spreg.utils import RegressionPropsY
from glm_fits import gauss_iwls, poiss_iwls, logit_iwls
import pysal.spreg.user_output as USER

__all__ = ['GLM']

class GLM(RegressionPropsY):
    """
    Generalised linear models. Can currently estimate Guassian, Poisson and
    Logisitc regression coefficients. GLM object prepares model input and fit
    method performs estimation which then returns a GLMResults object.

    Parameters
    ----------
        y             : array
                        n*1, dependent variable.
        x             : array
                        n*k, independent variable, exlcuding the constant.
        family        : string
                        Model type: 'Gaussian', 'Poisson', 'logistic'
        offset        : array
                        n*1, the offset variable at the ith location. For Poisson model
                        this term is often the size of the population at risk or
                        the expected size of the outcome in spatial epidemiology.
                        Default is None where Ni becomes 1.0 for all locations.
        y_fix         :

        sigma2_v1     : boolean
                        Sigma squared, True to use n as denominator.
                        Default is False which uses n-k.

    Attributes
    ----------
        y             : array
                        n*1, dependent variable.
        x             : array
                        n*k, independent variable, including constant.
        family        : string
                        Model type: 'Gaussian', 'Poisson', 'logistic'
        n             : integer
                        Number of observations
        k             : integer
                        Number of independent variables
        mean_y        : float
                        Mean of y
        std_y         : float
                        Standard deviation of y
        fit_params     : dict
                        Parameters passed into fit method to define estimation
                        routine.
    """
    def __init__(self, y, x, family='Gaussian', offset=None, y_fix = None, sigma2_v1=False):
        """
        Initialize class
        """
        self.n = USER.check_arrays(y, x)
        USER.check_y(y, self.n)
        self.y = y
        self.x = USER.check_constant(x)
        self.family = family
        self.k = x.shape[1]
        self.sigma2_v1=sigma2_v1
        if offset is None:
            self.offset = np.ones(shape=(self.n,1))
        else:
            self.offset = offset * 1.0
        if y_fix is None:
	        self.y_fix = np.zeros(shape=(self.n,1))
        else:
	        self.y_fix = y_fix
        self.fit_params = {}

    def fit(self, ini_betas=None, tol=1.0e-6, max_iter=200, solve='iwls'):
        """
        Method that fits a model with a particular estimation routine.

        Parameters
        ----------

        ini_betas     : array
                        k*1, initial coefficient values, including constant.
                        Default is None, which calculates initial values during
                        estimation.
        tol:            float
                        Tolerence for estimation convergence.
        max_iter       : integer
                        Maximum number of iterations if convergence not
                        achieved.
        solve         :string
                       Technique to solve MLE equations.
                       'iwls' = iteratively (re)weighted least squares (default)
        """
        self.fit_params['ini_betas'] = ini_betas
        self.fit_params['tol'] = tol
        self.fit_params['max_iter'] = max_iter
        self.fit_params['solve']=solve
        if solve.lower() == 'iwls':
            ey = self.y/self.offset
            if self.family == 'Gaussian':
                results = GLMResults(self, *gauss_iwls(self))
            if self.family == 'Poisson':
                results =  GLMResults(self, *poiss_iwls(self))
            if self.family == 'logistic':
            	results = GLMResults(self, *logit_iwls(self))
        return results


class GLMResults(GLM):
    """
    Results of estimated GLM and diagnostics.

    Parameters
    ----------
        model         : GLM object
                        Pointer to GLM object with estimation parameters.
        betas         : array
                        k*1, estimared coefficients
        predy         : array
                        n*1, predicted y values.
        v             : array
                        n*1, predicted y values before transformation via link.
        w             : array
                        n*1, final weight used for iwrl

    Attributes
    ----------
        model         : GLM Object
                        Points to GLM object for which parameters have been
                        estimated.
        y             : array
                        n*1, dependent variable.
        x             : array
                        n*k, independent variable, including constant.
        family        : string
                        Model type: 'Gaussian', 'Poisson', 'Logistic'
        n             : integer
                        Number of observations
        k             : integer
                        Number of independent variables
        fit_params     : dict
                        Parameters passed into fit method to define estimation
                        routine.
        sig2          : float
                        sigma squared used for subsequent computations.
        betas         : array
                        n*k, Beta estimation
        w             : array
                        n*1, final weight used for x
        v             : array
                        n*1, untransformed predicted functions.
                        Applying the link functions yields predy.
        xtxi          : array
                        n*k, inverse of xx' for computing covariance
        u             : array
                        n*1, residuals
        predy         : array
                        n*1, predicted value of y
        utu           : float
                        Sum of squared residuals
        sig2n         : float
                        sigma sqaured using n for denominator
        sig2n_k       : float
                        sigma sqaured using n-k for denominator
        vm            : array
                        Variance covariance matrix (kxk) of betas
        std_err       : array
                        k*1, standard errors of betas
        dev_u         : float
                        Deviance of residuals
    """

    def __init__(self, model, betas, predy, v=None, w=None):
        self.model = model
        self.n = model.n
        self.y = model.y
        self.x = model.x
        self.k = model.k
        self.family = model.family
        self.fit_params = model.fit_params
        self.betas = betas
        if v is not None:
            self.v = v
        if w is not None:
            self.w = w
        self.predy = predy
        self.u = self.y - self.predy
        self.xtxi = la.inv(np.dot(self.x.T,self.x))
        self._cache = {}

        if model.sigma2_v1:
	        self.sig2 = self.sig2n
        else:
            self.sig2 = self.sig2n_k

    @property
    def utu(self):
        try:
            return self._cache['utu']
        except AttributeError:
            self._cache = {}
            self._cache['utu'] = np.sum(self.u ** 2)
        except KeyError:
            self._cache['utu'] = np.sum(self.u ** 2)
        return self._cache['utu']

    @utu.setter
    def utu(self, val):
        try:
            self._cache['utu'] = val
        except AttributeError:
            self._cache = {}
            self._cache['utu'] = val
        except KeyError:
            self._cache['utu'] = val

    @property
    def sig2n(self):
        try:
            return self._cache['sig2n']
        except AttributeError:
            self._cache = {}
            self._cache['sig2n'] = np.sum(self.w*self.u**2) / self.n
        except KeyError:
            self._cache['sig2n'] = np.sum(self.w*self.u**2) / self.n
        return self._cache['sig2n']

    @sig2n.setter
    def sig2n(self, val):
        try:
            self._cache['sig2n'] = val
        except AttributeError:
            self._cache = {}
            self._cache['sig2n'] = val
        except KeyError:
            self._cache['sig2n'] = val

    @property
    def sig2n_k(self):
        try:
            return self._cache['sig2n_k']
        except AttributeError:
            self._cache = {}
            self._cache['sig2n_k'] = np.sum(self.w*self.u**2) / (self.n - self.k)
        except KeyError:
            self._cache['sig2n_k'] = np.sum(self.w*self.u**2) / (self.n - self.k)
        return self._cache['sig2n_k']

    @sig2n_k.setter
    def sig2n_k(self, val):
        try:
            self._cache['sig2n_k'] = val
        except AttributeError:
            self._cache = {}
            self._cache['sig2n_k'] = val
        except KeyError:
            self._cache['sig2n_k'] = val

    @property
    def vm(self):
        try:
            return self._cache['vm']
        except AttributeError:
            self._cache = {}
            if self.mType == 0:
        		self._cache['vm'] = np.dot(self.sig2, self.xtxi)
            else:
        	    xtw = (self.x * self.w).T
        	    xtwx = np.dot(xtw, self.x)
        	    self._cache['vm'] = la.inv(xtwx)
        except KeyError:
            if self.family == 'Gaussian':
        		self._cache['vm'] = np.dot(self.sig2, self.xtxi)
            else:
        	    xtw = (self.x * self.w).T
        	    xtwx = np.dot(xtw, self.x)
        	    self._cache['vm'] = la.inv(xtwx)
        return self._cache['vm']

    @vm.setter
    def vm(self, val):
        try:
            self._cache['vm'] = val
        except AttributeError:
            self._cache = {}
            self._cache['vm'] = val
        except KeyError:
            self._cache['vm'] = val

    @property
    def std_err(self):
        try:
            return self._cache['std_err']
        except AttributeError:
            self._cache = {}
            self._cache['std_err'] = np.sqrt(self.vm).diagonal()
        except KeyError:
            self._cache['std_err'] = np.sqrt(self.vm).diagonal()
        return self._cache['std_err']

    @std_err.setter
    def std_err(self, val):
        try:
            self._cache['std_err'] = val
        except AttributeError:
            self._cache = {}
            self._cache['std_err'] = val
        except KeyError:
            self._cache['std_err'] = val

    @property
    def dev_u(self):
        """
        deviance of residuals
        """
        try:
            return self._cache['dev_u']
        except AttributeError:
            self._cache = {}
            self._cache['dev_u'] = self.calc_dev_u()
        except KeyError:
            self._cache['dev_u'] = self.calc_dev_u()
        return self._cache['dev_u']

    @dev_u.setter
    def dev_u(self, val):
        try:
            self._cache['dev_u'] = val
        except AttributeError:
            self._cache = {}
            self._cache['dev_u'] = val
        except KeyError:
            self.cache['dev_u'] = val


    def calc_dev_u(self):
	dev = 0.0
	if self.family == 'Gaussian':
	    dev = self.n * (np.log(self.utu * 2.0 * np.pi / self.n) + 1.0)
	if self.family == 'Poisson':
	    id0 = self.y==0
	    id1 = self.y<>0
            if np.sum(id1) == self.n:
		dev = 2.0 * np.sum(self.y * np.log(self.y/self.predy))
            else:
                dev = 2.0 * (np.sum(self.y[id1] *
                    np.log(self.y[id1]/self.predy[id1])) -
                        np.sum(self.y[id0]-self.predy[id0]))
        if self.family == 'logistic':
            for i in range(self.n):
                if self.y[i] == 0:
                    dev += -2.0 * np.log(1.0 - self.predy[i])
                else:
                    dev += -2.0 * np.log(self.predy[i])
        return dev