import pandas as pd
def drawdown(returns_series:pd.Series):
  
    """take a time series of asset returns
    computes and returns a dataframe that contains:
    wealth index
    previous peaks
    percent drawdowns"""
   
    wealth_index=1000*(1+returns_series).cumprod()
    previous_peaks=wealth_index.cummax()
    drawdowns=(wealth_index - previous_peaks)/previous_peaks
    return pd.DataFrame({
        'Wealth':wealth_index,
        'Peaks':previous_peaks,
        'Drawdown':drawdowns 
    })
    
def get_ffme_returns():
    """load the Farma French dataset for the returns of top and bottom deciles by MarketCap"""
    me_m=pd.read_csv('Portfolios_Formed_on_ME_monthly_EW.csv',
                   header=0, index_col=0,na_values=-99.99)
    rets=me_m[['Lo 10','Hi 10']]
    rets.columns=['SmallCap','LargeCap']
    rets=rets/100
    rets.index=pd.to_datetime(rets.index,format='%Y%m').to_period('M')
    return rets

def get_hfi_returns():
    """load the Farma HF returns"""
    hfi=pd.read_csv('edhec-hedgefundindices.csv',
                   header=0, index_col=0,parse_dates=True)
    hfi=hfi/100
    hfi.index=hfi.index.to_period('M')
    return hfi

def get_ind_returns():
    """load and format 30 industry portfolios value weighted average monthly returns"""
    ind=pd.read_csv('ind30_m_vw_rets.csv',header=0,index_col=0,parse_dates=True)/100
    ind.index=pd.to_datetime(ind.index,format='%Y%m').to_period('M')
    ind.columns=ind.columns.str.strip()
    return ind

def get_ind_size():
    ind=pd.read_csv('ind30_m_size.csv',header=0,index_col=0,parse_dates=True)
    ind.index=pd.to_datetime(ind.index,format='%Y%m').to_period('M')
    ind.columns=ind.columns.str.strip()
    return ind

def get_ind_nfirms():
    ind=pd.read_csv('ind30_m_nfirms.csv',header=0,index_col=0,parse_dates=True)
    ind.index=pd.to_datetime(ind.index,format='%Y%m').to_period('M')
    ind.columns=ind.columns.str.strip()
    return ind

def get_total_market_return():
    ind_return=erk.get_ind_returns()
    ind_size=erk.get_ind_size()
    ind_nfirms=erk.get_ind_nfirms()
    ind_mktcap=ind_nfirms*ind_size
    total_mktcap=ind_mktcap.sum(axis='columns')
    ind_capweight=ind_mktcap.divide(total_mktcap,axis='rows')
    total_market_return=(ind_capweight*ind_return).sum(axis='columns')
    return total_market_return
    

def skewness(r):
    demeaned_r=r-r.mean()
    # use the population standard deviation, so set dof=0
    sigma_r=r.std(ddof=0)
    exp=((demeaned_r)**3).mean()
    return exp/sigma_r**3

def kurtosis(r):
    demeaned_r=r-r.mean()
    # use the population standard deviation, so set dof=0
    sigma_r=r.std(ddof=0)
    exp=((demeaned_r)**4).mean()
    return exp/sigma_r**4

import scipy.stats
def is_normal(r, level=0.01):
    """apply jarque_bera test to see if a series is normal,
    test is applied 1% by default, return True if series is normally distributed"""
    statistics, p_values=scipy.stats.jarque_bera(r)
    return p_values>level
    
def semideviation(r):
    """return semideviation aka negative semideviation of r"""
    is_negative=r<0
    return r[is_negative].std(ddof=0)

import numpy as np
def var_historic(r,level=5):
    if isinstance(r,pd.DataFrame):
        return r.aggregate(var_historic, level=level)
    elif isinstance(r,pd.Series):
        return -np.percentile(r,level)
    else:
        raise TypeError('Expect r to be series or dataframe')


from scipy.stats import norm
def var_gaussian(r,level=5, modified=False):
    """compute Z score assuming it is Gaussian"""
    z= norm.ppf(level/100)
    if modified:
        # modified Z score based on observed S and K
        s=skewness(r)
        k=kurtosis(r)
        z = (z + (z**2 - 1)*s/6 + (z**3 - 3*z)*(k-3)/24 - (2 * z**3 - 5*z)*(s**2)/36)  
    return -(r.mean()+z*r.std(ddof=0))

def cvar_historic(r,level=5):
    if isinstance(r,pd.Series):
        is_beyond=r<=-var_historic(r,level=level)
        return -r[is_beyond].mean()
    elif isinstance(r,pd.DataFrame):
        return r.aggregate(cvar_historic,level=level)
    else:
        raise TypeError('Expect r to be series or dataframe')

def annualized_vol(r,periods_per_year):
    return r.std()*(periods_per_year**0.5)

def annualized_rets(r,periods_per_year):
    compounded_growth=(1+r).prod()
    n_periods=r.shape[0]
    return (compounded_growth**(periods_per_year/n_periods))-1

def sharpe_ratio(r,riskfree_rate,periods_per_year):
    #convert annualized rf rate to period
    rf_per_period=(1+riskfree_rate)**(1/periods_per_year)-1
    excess_ret=r-rf_per_period
    ann_ex_ret=annualized_rets(excess_ret,periods_per_year)
    ann_vol=annualized_vol(r,periods_per_year)
    return ann_ex_ret/ann_vol

def portfolio_return(weights,returns):
    """weights to returns"""
    return weights.T@returns

def portfolio_vol(weights,covmat):
    """weights to vol"""
    return ((weights.T)@covmat@weights)**0.5

import edhec_risk_kit as erk
def plot_ef2(n_points,er,cov,style=".-"):
    """plot 2 assets ef"""
    if er.shape[0]!=2:
        raise TypeError('Expect r to be series or dataframe')
    weights=[np.array([w,1-w]) for w in np.linspace(0,1,n_points)]
    rets=[erk.portfolio_return(w,er) for w in weights]
    vols=[erk.portfolio_vol(w,cov) for w in weights]
    ef=pd.DataFrame({'Returns':rets,'Volatility':vols})
    return ef.plot.line(x='Volatility',y='Returns',style=style)

import numpy as np
from scipy.optimize import minimize
def minimize_vol(target_r,er,cov):
    """target return to W"""
    n=er.shape[0]
    init_guess=np.repeat(1/n,n)
    bounds=((0,1),)*n
    return_is_target={
        'type':'eq',
        'args':(er,),
        'fun':lambda weights, er:target_r-portfolio_return(weights,er)
    }
    weights_sum_to_1={
        'type':'eq',
        'fun':lambda weights: np.sum(weights)-1
    }
    results=minimize(portfolio_vol,init_guess,
                    args=(cov,),method='SLSQP',options={'disp':False},
                    constraints=(return_is_target,weights_sum_to_1),
                    bounds=bounds)
    return results.x

import pandas as pd
def optiminal_weights(n_points,er,cov):
    """generate list of weights to run the optimizer to minimize the vol"""
    target_rs=np.linspace(er.min(),er.max(),n_points)
    weights=[minimize_vol(target_return,er,cov) for target_return in target_rs]
    return weights

from scipy.optimize import minimize
def msr(riskfree_rate,er,cov):
    """rf rate, er, cov to W"""
    n=er.shape[0]
    init_guess=np.repeat(1/n,n)
    bounds=((0,1),)*n

    weights_sum_to_1={
        'type':'eq',
        'fun':lambda weights: np.sum(weights)-1
    }
    def neg_sharpe_ratio(weights,riskfree_rate,er,cov):
        """minimize the negative sharpe ratio to get the max value"""
        r=portfolio_return(weights,er)
        vol=portfolio_vol(weights,cov)
        return -(r-riskfree_rate)/vol
    
    results=minimize(neg_sharpe_ratio,init_guess,
                    args=(riskfree_rate,er,cov,),method='SLSQP',options={'disp':False},
                    constraints=(weights_sum_to_1),
                    bounds=bounds)
    return results.x
def gmv(cov):
    """return the weights of the global min vol portfolio given cov matrix
    call msr function, input the same ER (if all ER are the same, the only way to increase sharpe ratio is through min vol
    """
    n=cov.shape[0]
    return msr(0,np.repeat(1,n),cov)
    
def plot_ef(n_points,er,cov,style=".-",show_cml=False,riskfree_rate=0, show_ew=False, show_gmv=False):
    """plot N assets ef"""
    weights=optiminal_weights(n_points,er,cov)
    rets=[portfolio_return(w,er) for w in weights]
    vols=[portfolio_vol(w,cov) for w in weights]
    ef=pd.DataFrame({'Returns':rets,'Volatility':vols})
    ax= ef.plot.line(x='Volatility',y='Returns',style=style)
    if show_ew:
        n=er.shape[0]
        w_ew=np.repeat(1/n,n)
        r_ew=portfolio_return(w_ew,er)
        vol_ew=portfolio_vol(w_ew,cov)
        # display EW
        ax.plot([vol_ew],[r_ew],color='goldenrod',marker='o',markersize=12)
    if show_gmv:
        w_gmv=gmv(cov)
        
        r_gmv=portfolio_return(w_gmv,er)
        vol_gmv=portfolio_vol(w_gmv,cov)
        # display EW
        ax.plot([vol_gmv],[r_gmv],color='midnightblue',marker='o',markersize=10)        
    if show_cml:
        ax.set_xlim(left=0) ##set x axis limit to start with 0
        
        w_msr=msr(riskfree_rate,er,cov)
        r_msr=portfolio_return(w_msr,er)
        vol_msr=portfolio_vol(w_msr,cov)
        # add CML
        cml_x=[0,vol_msr]
        cml_y=[riskfree_rate,r_msr]
        ax.plot(cml_x,cml_y,color='green',marker='o',linestyle='dashed',markersize=12,linewidth=2)
    return ax

def run_cppi(risky_r,safe_r=None,m=3,start=1000,floor=0.8,riskfree_rate=0.03,drawdown=None):
    """run a backtest of CPPI strategy, given a set of returns of risky assets"""
    # set up CPPI parameters
    dates=risky_r.index
    n_steps=len(dates)
    account_value=start
    floor_value=start*floor
    peak=start
    if isinstance(risky_r, pd.Series):
        risky_r=pd.DataFrame(risky_r,columns=['R'])
    if safe_r is None:
        safe_r=pd.DataFrame().reindex_like(risky_r)
        safe_r.values[:]=riskfree_rate/12 # fast way to set all values to numbers
    # set up dataframe for saving intermediate values    
    account_history=pd.DataFrame().reindex_like(risky_r)
    cushion_history=pd.DataFrame().reindex_like(risky_r)
    risky_w_history=pd.DataFrame().reindex_like(risky_r)

    for step in range(n_steps):
        if drawdown is not None:
            peak=np.maximum(peak,account_value)
            floor_value=peak*(1-drawdown)
        cushion=(account_value-floor_value)/account_value
        risky_w=m*cushion
        risky_w=np.minimum(risky_w,1)
        risky_w=np.maximum(risky_w,0)
        safe_w=1-risky_w
        risky_alloc=account_value*risky_w
        safe_alloc=account_value*safe_w
        ## update the account value for this time step
        account_value=risky_alloc*(1+risky_r.iloc[step])+safe_alloc*(1+safe_r.iloc[step])
        # save the values so that I can look at the history and plot it
        cushion_history.iloc[step]=cushion
        account_history.iloc[step]=account_value
        risky_w_history.iloc[step]=risky_w
    risky_wealth=start*(1+risky_r).cumprod()
    backtest_result={
          "Wealth":account_history,
          'Risky Wealth':risky_wealth,
          'Risky Budget':cushion_history,
          'Risky Allocation':risky_w_history,
          'm':m,
          'start':start,
          'floor':floor,
          'risky_r':risky_r,
          'safe_r':safe_r
    }
    return backtest_result

def summary_stats(r,riskfree_rate=0.03):
    ann_r=r.aggregate(annualized_rets,periods_per_year=12)
    ann_vol=r.aggregate(annualized_vol,periods_per_year=12)
    ann_sr=r.aggregate(sharpe_ratio,riskfree_rate=riskfree_rate,periods_per_year=12)
    dd=r.aggregate(lambda r:drawdown(r).Drawdown.min())
    skew=r.aggregate(skewness)
    kurt=r.aggregate(kurtosis)
    cf_var5=r.aggregate(var_gaussian,modified=True)
    hist_cvar5=r.aggregate(cvar_historic)
    return pd.DataFrame({
        'annualized return':ann_r,
        'annualized vol':ann_vol,
        'skewness':skew,
        'kurtosis':kurt,
        'cornish-fisher var 5%':cf_var5,
        'historic cvar 5%':hist_cvar5,
        'sharpe ratio':ann_sr,
        'max drawdown':dd
    })

def gbm0(n_years=10, n_scenarios=1000, mu=0.17, sigma=0.15, steps_per_year=12,s_0=100):
    """evolution of stock price using geometric brownian motion model"""
    dt=1/steps_per_year
    n_steps=int(n_years*steps_per_year)
    rets_plus_one=np.random.normal(loc=1+mu*dt,scale=(sigma*np.sqrt(dt)),size=(n_steps,n_scenarios))
    rets_plus_one[0]=1
    prices=s_0*pd.DataFrame(rets_plus_one).cumprod()
    return prices  

def gbm(n_years = 10, n_scenarios=1000, mu=0.07, sigma=0.15, steps_per_year=12, s_0=100.0, prices=True):
    """
    Evolution of Geometric Brownian Motion trajectories, such as for Stock Prices through Monte Carlo
    :param n_years:  The number of years to generate data for
    :param n_paths: The number of scenarios/trajectories
    :param mu: Annualized Drift, e.g. Market Return
    :param sigma: Annualized Volatility
    :param steps_per_year: granularity of the simulation
    :param s_0: initial value
    :return: a numpy array of n_paths columns and n_years*steps_per_year rows
    """
    # Derive per-step Model Parameters from User Specifications
    dt = 1/steps_per_year
    n_steps = int(n_years*steps_per_year) + 1
    # the standard way ...
    # rets_plus_1 = np.random.normal(loc=mu*dt+1, scale=sigma*np.sqrt(dt), size=(n_steps, n_scenarios))
    # without discretization error ...
    rets_plus_1 = np.random.normal(loc=(1+mu)**dt, scale=(sigma*np.sqrt(dt)), size=(n_steps, n_scenarios))
    rets_plus_1[0] = 1
    ret_val = s_0*pd.DataFrame(rets_plus_1).cumprod() if prices else rets_plus_1-1
    return ret_val

def discount0(t,r):
    """compute the price of a pure discount bond that pay 1 dollar at time t given int rate r, assume int rate is flat"""
    return (1+r)**(-t)

def discount(t,r):
    """compute the price of a pure discount bond that pays 1 dollar at time period t
    r is the per period int rate
    returns a t*r series dataframe indexed by t"""
    discounts=pd.DataFrame([(r+1)**-i for i in t])
    discounts.index=t
    return discounts
    

def pv0(l,r):
    """compute the pv of a sequence of liability, l is indexed by the time and the values are the amounts if liability"""
    dates=l.index
    discounts=discount(dates,r)
    return (discounts*l).sum()

def pv(flows,r):
    dates=flows.index
    discounts=discount(dates,r)
    return discounts.multiply(flows,axis='rows').sum()
    

def funding_ratio(assets,liabilities,r):
    return pv(assets,r)/pv(liabilities,r)

def bond_cash_flows(maturity=5, principle=100, coupon_rate=0.03, coupons_per_year=12):
    """return a series of CF generated by bond, indexed by a coupon number"""
    n_coupons=round(maturity*coupons_per_year)
    coupon_amt=principle*coupon_rate/coupons_per_year
    coupons=np.repeat(coupon_amt,n_coupons)
    coupon_times=np.arange(1,n_coupons+1)
    cash_flows=pd.Series(data=coupon_amt,index=coupon_times)
    cash_flows.iloc[-1]+=principle
    return cash_flows

def bond_price0(maturity, principle=100, coupon_rate=0.03, coupons_per_year=12, discount_rate=0.03):
    """price a bond"""
    cash_flows=bond_cash_flows(maturity, principle, coupon_rate, coupons_per_year)
    return pv(cash_flows, discount_rate/coupons_per_year)

def bond_price(maturity, principle=100, coupon_rate=0.03, coupons_per_year=12, rates=0.03):
    """compute the price if the discount rate is not just a number"""
    if isinstance(rates, pd.DataFrame): # generate bond prices for every single time
        pricing_dates=rates.index
        prices=pd.DataFrame(index=pricing_dates,columns=rates.columns)
        for t in pricing_dates:
            prices.loc[t]=bond_price(maturity-t/coupons_per_year,principle,coupon_rate,coupons_per_year,rates.loc[t])
        return prices
    else: # base case, single time period
        if maturity<=0: return principle+principle*coupon_rate/coupons_per_year
        cash_flows=bond_cash_flows(maturity, principle, coupon_rate, coupons_per_year)
        return pv(cash_flows, rates/coupons_per_year)

def macaulay_duration(flows,discount_rate):
    """comopute mac duration of a sequence of cf"""
    discounted_flows=discount(flows.index,discount_rate)*flows
    weights=discounted_flows/discounted_flows.sum()
    return np.average(flows.index,weights=weights) ## np weighted-average function

def match_durations(cf_t,cf_s,cf_l,discount_rate):
    """return the weights w, 1-w that match target duration"""
    d_t=macaulay_duration(cf_t,discount_rate)
    d_s=macaulay_duration(cf_s,discount_rate)
    d_l=macaulay_duration(cf_l,discount_rate)
    return (d_l-d_t)/(d_l-d_s)

import math
def cir(n_years=10, n_scenarios=1, a=0.05, b=0.03, sigma=0.05, steps_per_year=12, r_0=None):
    """implement CIR for int rate, a is speed to revert, b is LT mean"""
    if r_0 is None: r_0=b
    r_0=ann_to_inst(r_0)
    dt=1/steps_per_year
    # sacle is the sigma
    num_steps=int(n_years*steps_per_year)+1
    # plus 1 because we want to initialize array of rates, contain initial rate at row 0
    shock=np.random.normal(0,scale=np.sqrt(dt),size=(num_steps,n_scenarios))
    rates=np.empty_like(shock)
    rates[0]=r_0
    ## for price generation
    h=math.sqrt(a**2+2*sigma**2)
    prices=np.empty_like(shock)
    
    def price(ttm,r):
        _A=((2*h*math.exp((h+a)*ttm/2))/(2*h+(h+a)*(math.exp(h*ttm)-1)))**(2*a*b/sigma**2)
        _B=(2*(math.exp(h*ttm)-1))/(2*h+(h+a)*(math.exp(h*ttm)-1))
        _P=_A*np.exp(-_B*r)
        return _P
    prices[0]=price(n_years,r_0)
    # start with 1 because we already filled 0 with r_0
    for step in range(1,num_steps):
        # d_rt is the change in rate
        r_t=rates[step-1]
        d_r_t=a*(b-r_t)*dt+sigma*np.sqrt(r_t)*shock[step]
        rates[step]=abs(r_t+d_r_t)
        ## generating price at time t as well
        prices[step]=price(n_years-step*dt,rates[step])
    rates=pd.DataFrame(data=inst_to_ann(rates),index=range(num_steps))
    prices=pd.DataFrame(data=prices,index=range(num_steps))
    return rates, prices

def inst_to_ann(r):
    """convert short rate to annualized rate"""
    return np.expm1(r)
## m1 means minus 1

def ann_to_inst(r):
    """convert ann rate to short rate"""
    return np.log1p(r)
# 1p means plus 1

def bond_total_return(monthly_prices,principal,coupon_rate,coupons_per_year):
    """compute the bond total return based on bond prices and coupon payments"""
    coupons=pd.DataFrame(data=0, index=monthly_prices.index,columns=monthly_prices.columns)
    t_max=monthly_prices.index.max()
    pay_date=np.linspace(12/coupons_per_year,t_max,int(coupons_per_year*t_max/12),dtype=int)
    coupons.iloc[pay_date]=principal*coupon_rate/coupons_per_year
    total_returns=(monthly_prices+coupons)/monthly_prices.shift()-1
    return total_returns.dropna()

# define a backtest by allocation between two assets,# keyword argument, accept any argument/parameter you input
def bt_mix(r1,r2,allocator,**kwargs):
    """r1,r2 are T*N dataframes returns, T is time step, N is # of scenarios,
    allocation to the 1st portfolio return a T*1 dataframe
    return a T*N dataframe for N scenarios"""
    if not r1.shape==r2.shape:
        raise ValueError('r1, r2 need to be the same shape')
    weights=allocator(r1,r2,**kwargs)
    if not weights.shape==r1.shape:
        raise ValueError('allocator weights and r1 and r2 need to be the same')
    r_mix=weights*r1+(1-weights)*r2
    return r_mix

def fixedmix_allocator(r1,r2,w1,**kwargs):
    """produce a time series over T steps of allocation between PSP and GHP across N scenarios
       row is price of time step, column is scenario
       return T*N dataframe of PSP weights"""
    return pd.DataFrame(data=w1,index=r1.index,columns=r1.columns)

def terminal_values(rets):
    """return the final values of a dollar at the end of return period for wach scenario"""
    return (rets+1).prod()

def termianl_stats(rets,floor=0.8,cap=np.inf,name='Stats'):
    terminal_wealth=(rets+1).prod()
    breach=terminal_wealth<floor
    reach=terminal_wealth>=cap
    p_breach=breach.mean() if breach.sum()>0 else np.nan # how often does breach happen?
    p_reach=breach.mean() if reach.sum()>0 else np.nan
    e_short=(floor-terminal_wealth[breach]).mean() if breach.sum()>0 else np.nan # expected shortfall
    e_surplus=(cap-terminal_wealth[reach]).mean() if reach.sum()>0 else np.nan
    sum_stats=pd.DataFrame.from_dict({
        'mean':terminal_wealth.mean(),
        'std':terminal_wealth.std(),
        "p_breach":p_breach,
        "e_short":e_short,
        "p_reach":p_reach,
        "e_surplus":e_surplus},
        orient='index',columns=[name])
    return sum_stats
        
def glidepath_allocator(r1,r2,start_glide=1,end_glide=0):
    """simulate a target date fund style gradual move from r1 to r2"""
    n_points=r1.shape[0]
    n_col=r1.shape[1]
    path=pd.Series(data=np.linspace(start_glide,end_glide,num=n_points))
    paths=pd.concat([path]*n_col,axis=1)
    paths.index=r1.index
    paths.columns=r1.columns
    return paths        
    
