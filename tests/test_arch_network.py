import pytest

@pytest.mark.parametrize("case", [
    {"type": "lstm"},
    {"type": "gcn"},
    {"type": "cellss-flow"}
])
def test_arch_embedder(case):
    from aw_nas.common import get_search_space
    from aw_nas.evaluator.arch_network import ArchEmbedder
    search_space = get_search_space(cls="cnn")
    device = "cuda"
    cls = ArchEmbedder.get_class_(case["type"])
    embedder = cls(search_space)
    embedder.to(device)

    batch_size = 4
    rollouts = [search_space.random_sample() for _ in range(batch_size)]
    archs = [r.arch for r in rollouts]

    arch_embedding = embedder(archs)
    assert arch_embedding.shape[0] == batch_size
    assert arch_embedding.shape[1] == embedder.out_dim

def test_gcnflow_arch_embedder_utils():
    from aw_nas.evaluator.arch_network import GCNFlowArchEmbedder
    from aw_nas.common import get_search_space

    search_space = get_search_space(cls="cnn")
    device = "cuda"
    embedder = GCNFlowArchEmbedder(search_space)
    embedder.to(device)

    batch_size = 4
    rollouts = [search_space.random_sample() for _ in range(batch_size)]
    archs = [r.arch for r in rollouts]
    adj_matrices, adj_op_inds_lst, x = embedder.embed_and_transform_arch(archs)
    assert search_space.num_init_nodes == len(adj_op_inds_lst)
    for i in range(batch_size):
        for j in range(search_space.num_cell_groups):
            for idx, (from_node, op) in enumerate(zip(rollouts[i].arch[j][0], rollouts[i].arch[j][1])):
                assert adj_op_inds_lst[idx % 2][i, j][idx // 2 + 2, from_node] == op

def test_gcn_arch_embedder_utils():
    from aw_nas.evaluator.arch_network import GCNArchEmbedder
    from aw_nas.common import get_search_space
    search_space = get_search_space(cls="cnn")
    device = "cuda"
    embedder = GCNArchEmbedder(search_space)
    embedder.to(device)

    batch_size = 4
    rollouts = [search_space.random_sample() for _ in range(batch_size)]
    archs = [r.arch for r in rollouts]
    adj_matrices, node_embed = embedder.embed_and_transform_arch(archs)
    _num_nodes = search_space.num_steps + search_space.num_init_nodes
    assert adj_matrices.shape == (batch_size, search_space.num_cell_groups,
                                  _num_nodes, _num_nodes)
    assert node_embed.shape == (batch_size, search_space.num_cell_groups,
                                _num_nodes, embedder.op_dim)

def test_arch_comparator():
    from aw_nas.common import get_search_space
    from aw_nas.evaluator.arch_network import PointwiseComparator
    search_space = get_search_space(cls="cnn")
    device = "cuda"
    comparator = PointwiseComparator(search_space)
    comparator.to(device)

    batch_size = 4
    archs_1 = [search_space.random_sample().arch for _ in range(batch_size)]
    archs_2 = [search_space.random_sample().arch for _ in range(batch_size)]

    # forward
    scores = comparator.predict(archs_1)
    assert len(scores) == batch_size
    compare_res = comparator.compare(archs_1, archs_2)
    assert len(compare_res) == batch_size

    # update
    comparator.update_predict(archs_1, [0.1, 0.3, 0.4, 0.9])
    comparator.update_compare(archs_1, archs_2, [0.1, 0.3, 0.4, 0.9])

@pytest.mark.parametrize("case", [
    {"pairing_method": "concat"},
    {"pairing_method": "diff"}
])
def test_pairwise_arch_comparator(case):
    from aw_nas.common import get_search_space
    from aw_nas.evaluator.arch_network import PairwiseComparator
    search_space = get_search_space(cls="cnn")
    device = "cuda"
    comparator = PairwiseComparator(search_space, **case)
    comparator.to(device)

    batch_size = 4
    archs_1 = [search_space.random_sample().arch for _ in range(batch_size)]
    archs_2 = [search_space.random_sample().arch for _ in range(batch_size)]

    # forward
    before_inds = comparator.argsort_list(archs_1 + archs_2, batch_size=2)
    print(before_inds)
    before_res = comparator.compare(archs_1, archs_2)
    assert len(before_res) == batch_size
    print("[before] compare res: ", before_res)

    # update
    for _ in range(20):
        comparator.update_compare(archs_1, archs_2, [0, 1, 1, 1])
    after_inds = comparator.argsort_list(archs_1 + archs_2, batch_size=2)
    print(after_inds)
    after_res = comparator.compare(archs_1, archs_2)
    assert len(after_res) == batch_size
    print("[after] compare res: ", after_res)