from io import BytesIO
import unittest

import joblib
import numpy as np

from nlp_model.train_tfidf import search, train_model


class TrainTfidfTests(unittest.TestCase):
    def setUp(self):
        self.dataset = {
            "schema_version": 1,
            "texts": ["Кто ещё играет?", "Когда ужин?", "Опять проиграли"],
            "replies": ["Зовите!", "В восемь", "Это разминка"],
        }

    def test_roundtrip_and_search(self):
        model = train_model(self.dataset)
        stream = BytesIO()
        joblib.dump(model, stream)
        stream.seek(0)
        restored = joblib.load(stream)
        match = search(restored, "КТО ЕЩЕ ИГРАЕТ?")[0]
        self.assertEqual(match["reply"], "Зовите!")
        self.assertAlmostEqual(match["score"], 1, places=5)
        self.assertEqual(restored["word_index"].dtype, np.float32)
        self.assertEqual(restored["word_index"].shape[0], len(restored["replies"]))

    def test_empty_and_unknown_queries_do_not_return_arbitrary_replies(self):
        model = train_model(self.dataset)
        self.assertEqual(search(model, ""), [])
        self.assertEqual(search(model, "xyzxyz", threshold=0), [])
        self.assertEqual(len(search(model, "играет", top_k=1)), 1)

    def test_rejects_invalid_datasets(self):
        for dataset in ({}, {"schema_version": 1, "texts": [], "replies": []},
                        {"schema_version": 1, "texts": ["Hi"], "replies": []}):
            with self.assertRaises(ValueError):
                train_model(dataset)


if __name__ == "__main__":
    unittest.main()
