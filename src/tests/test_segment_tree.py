from collections import deque

import numpy as np
import pytest

from src.segment_tree import SegmentTree, SymbolData


class TestSegmentTree:
    def test_init(self):
        tree = SegmentTree()
        assert isinstance(tree.buffer, deque)
        assert tree.tree_min == []
        assert tree.tree_max == []
        assert tree.tree_sum == []
        assert tree.tree_sum_sq == []
        assert tree.last_val is None
        assert tree.is_dirty is True

    def test_add_batch_single_value(self):
        tree = SegmentTree()
        tree.add_batch([5.0])
        assert list(tree.buffer) == [5.0]
        assert tree.last_val == 5.0
        assert tree.is_dirty is True

    def test_add_batch_multiple_values(self):
        tree = SegmentTree()
        tree.add_batch([1.0, 2.0, 3.0])
        assert list(tree.buffer) == [1.0, 2.0, 3.0]
        assert tree.last_val == 3.0
        assert tree.is_dirty is True

    def test_add_batch_multiple_calls(self):
        tree = SegmentTree()
        tree.add_batch([1.0, 2.0])
        tree.add_batch([3.0, 4.0])
        assert list(tree.buffer) == [1.0, 2.0, 3.0, 4.0]
        assert tree.last_val == 4.0
        assert tree.is_dirty is True

    def test_build_tree_empty(self):
        tree = SegmentTree()
        tree._build_tree()
        assert tree.tree_min == []
        assert tree.tree_max == []
        assert tree.tree_sum == []
        assert tree.tree_sum_sq == []
        assert tree.is_dirty is True

    def test_build_tree_non_empty(self):
        tree = SegmentTree()
        tree.add_batch([1.0, 3.0, 2.0])
        tree._build_tree()
        assert len(tree.tree_min) > 0
        assert len(tree.tree_max) > 0
        assert len(tree.tree_sum) > 0
        assert len(tree.tree_sum_sq) > 0
        assert tree.is_dirty is False

    def test_get_stats_empty(self):
        tree = SegmentTree()
        stats = tree.get_stats(1)
        assert stats is None

    def test_get_stats_single_value(self):
        tree = SegmentTree()
        tree.add_batch([5.0])
        stats = tree.get_stats(1)
        assert stats.min == 5.0
        assert stats.max == 5.0
        assert stats.last == 5.0
        assert stats.avg == 5.0
        assert stats.var == 0.0

    def test_get_stats_multiple_values(self):
        tree = SegmentTree()
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        tree.add_batch(values)

        stats = tree.get_stats(1)
        assert stats.min == 1.0
        assert stats.max == 5.0
        assert stats.last == 5.0
        assert stats.avg == 3.0
        assert pytest.approx(stats.var) == 2.0

    def test_get_stats_subset_of_values(self):
        tree = SegmentTree()
        values = [float(i) for i in range(1, 21)]  # 20 values
        tree.add_batch(values)

        # Test with k=1 (should use last 10 values)
        stats = tree.get_stats(1)
        assert stats.min == 11.0
        assert stats.max == 20.0
        assert stats.last == 20.0
        assert stats.avg == 15.5

        # Check variance calculation
        subset = [float(i) for i in range(11, 21)]
        expected_variance = np.var(subset)
        assert pytest.approx(stats.var) == expected_variance

    def test_build_tree_after_add(self):
        tree = SegmentTree()
        tree.add_batch([1.0, 2.0, 3.0])
        assert tree.is_dirty is True

        # Getting stats triggers tree build
        tree.get_stats(1)
        assert tree.is_dirty is False

        # Adding more data marks tree as dirty again
        tree.add_batch([4.0, 5.0])
        assert tree.is_dirty is True


class TestSymbolData:
    def test_init(self):
        symbol_data = SymbolData()
        assert isinstance(symbol_data.segment_tree, SegmentTree)
        assert symbol_data.stats_cache == {}

    def test_add_batch(self):
        symbol_data = SymbolData()
        symbol_data.add_batch([1.0, 2.0, 3.0])
        assert list(symbol_data.segment_tree.buffer) == [1.0, 2.0, 3.0]
        assert symbol_data.stats_cache == {}  # Cache should be cleared

    def test_get_stats(self):
        symbol_data = SymbolData()
        symbol_data.add_batch([1.0, 2.0, 3.0, 4.0, 5.0])

        # First call should calculate and cache
        stats1 = symbol_data.get_stats(1)
        assert stats1.min == 1.0
        assert stats1.max == 5.0
        assert len(symbol_data.stats_cache) == 1
        assert 1 in symbol_data.stats_cache

        # Second call should use cache
        stats2 = symbol_data.get_stats(1)
        assert stats2 == stats1

        symbol_data.add_batch(
            [
                6.0,
                7.0,
                8.0,
                9.0,
                10.0,
                11.0,
                12.0,
                13.0,
                14.0,
                15.0,
            ]
        )

        stats1 = symbol_data.get_stats(1)
        assert stats1.min == 6.0
        assert stats1.max == 15.0
        assert len(symbol_data.stats_cache) == 1

        # Different k should calculate new stats
        stats3 = symbol_data.get_stats(2)
        assert 2 in symbol_data.stats_cache
        assert stats3 != stats1

        # Adding new data should clear cache
        symbol_data.add_batch([6.0])
        assert symbol_data.stats_cache == {}

    def test_get_stats_no_data(self):
        symbol_data = SymbolData()
        assert symbol_data.get_stats(1) is None


class TestEdgeCases:
    def test_buffer_max_size(self):
        """Test that buffer respects maximum size"""
        tree = SegmentTree(max_size=5)
        tree.add_batch([1.0, 2.0, 3.0, 4.0, 5.0])
        tree.add_batch([6.0, 7.0])
        # Should only keep the most recent 5 values
        assert list(tree.buffer) == [3.0, 4.0, 5.0, 6.0, 7.0]

    def test_precision_with_floating_point(self):
        """Test handling of floating point precision"""
        tree = SegmentTree()
        tree.add_batch([1.1, 2.2, 3.3, 4.4, 5.5])
        stats = tree.get_stats(1)
        assert stats.min == 1.1
        assert stats.max == 5.5
        assert stats.last == 5.5
        assert pytest.approx(stats.avg) == 3.3
        assert pytest.approx(stats.var) == 2.42
