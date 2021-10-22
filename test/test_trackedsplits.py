import unittest
from trackedsplits import RBYSplits

class TestTrackedSplits(unittest.TestCase):
    def test_basic_success(self):
        splits = RBYSplits()
        nido = splits['Nido']
        self.assertEqual(nido.Position, 2)
        self.assertEqual(nido.Name, 'Nidoran')

        nido = splits['NidoranM']
        self.assertEqual(nido.Position, 2)
        self.assertEqual(nido.Name, 'Nidoran')

        self.assertIsNotNone(splits['Bridge'])

    def test_failure_case(self):
        splits = RBYSplits()
        nido = splits['Nidorino']
        self.assertIsNone(nido)

if __name__ == '__main__':
    unittest.main()
