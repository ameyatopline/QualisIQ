import numpy as np
from sklearn.ensemble import IsolationForest
from ml.runtime import scores,vector

def test_portable_forest_matches_reference():
    rng=np.random.default_rng(123);x=rng.normal(size=(300,2)).astype(np.float32)
    forest=IsolationForest(n_estimators=7,max_samples=64,random_state=123).fit(x)
    artifact={'max_samples':64,'trees':[]}
    for estimator in forest.estimators_:
        t=estimator.tree_;artifact['trees'].append({'feature':t.feature.tolist(),'threshold':t.threshold.tolist(),'left':t.children_left.tolist(),'right':t.children_right.tolist(),'n':t.n_node_samples.tolist()})
    np.testing.assert_allclose(scores(x,artifact),-forest.score_samples(x),atol=1e-12)
    assert vector(12,{'median':10,'scale':2})==[1,1]
