from pyomo import environ as pe

def create_model():
    
    m = pe.AbstractModel()
    
    m.n_days = pe.Param(
        within=pe.PositiveIntegers,
        doc='''Number of days.'''
    )
    
    m.n_clusters = pe.Param(
        within=pe.PositiveIntegers,
        doc='''Number of clusters.'''
    )
    
    m.n_extreme_days = pe.Param(
        within=pe.NonNegativeIntegers,
        initialize=0,
        doc='''Number of extreme days.'''
    )
    
    #====================================#
    #                 Sets
    #====================================#
    
    m.Days = pe.RangeSet(m.n_days)
    
    m.Days_cross = pe.Set(
        initialize=m.Days*m.Days,
        doc=''''''
    )
    
    m.Clusters = pe.RangeSet(m.n_clusters)
    
    #====================================#
    #            Parameters
    #====================================#
    
    m.distance = pe.Param(m.Days_cross)
    
    #====================================#
    #             Variables
    #====================================#
    
    m.z = pe.Var(
        m.Days_cross, 
        within = pe.Binary,
        initialize=0,
        doc = '''1 iff object j is assigned to the cluster 
        whose representative element is object i.'''
    )
    
    m.y = pe.Var(
        m.Days, 
        within = pe.Binary,
        initialize=0,
        doc = '''1 iff object i is chosen as representative 
        of its cluster.'''
    )
    
    #====================================#
    #             Constraints
    #====================================#
    
    def _total_representative_days(m):
        return sum(m.y[i] for i in m.Days) == m.n_clusters
    
    m.total_representative_days = pe.Constraint(
        rule = _total_representative_days,
        doc = '''One representative day for each cluster.'''
    )
    
    def _each_non_extreme_day_is_represented(m, j):
        return sum(m.z[i,j] for i in m.Days) <= 1
    
    m.each_non_extreme_day_is_represented = pe.Constraint(
        m.Days,
        rule = _each_non_extreme_day_is_represented,
        doc='''each day is represented by exactly 1 day 
        (without EDs)'''
    )
    
    def _total_represented_days(m):
        return sum(m.z[ij] for ij in m.Days_cross) == m.n_days - m.n_extreme_days
    
    m.total_represented_days = pe.Constraint(
        rule = _total_represented_days,
        doc = '''All non-extreme days are represented.'''
    )
    
    def _represented_by_representative(m, i, j):
        return m.z[i,j] <= m.y[i]
    
    m.represented_by_representative = pe.Constraint(
        m.Days_cross,
        rule = _represented_by_representative,
        doc = '''Days can only be represented by 
        representative days.'''
    )
    
    #====================================#
    #           Objective Function
    #====================================#
    
    def _total_distance(m):
        return sum(m.distance[ij]*m.z[ij] for ij in m.Days_cross)
        
    
    m.minimize_total_distance = pe.Objective(
        rule=_total_distance,
        doc='''Mininimize total distance between days 
        of the same cluster.'''        
    )
    
    return m
    
    
    
    
    