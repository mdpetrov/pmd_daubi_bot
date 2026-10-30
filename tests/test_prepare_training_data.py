import unittest

from nlp_model.prepare_training_data import prepare_training_data


def message(identifier, text, **kwargs):
    return dict(id=identifier, type="message", text=text, **kwargs)


class PrepareTrainingDataTests(unittest.TestCase):
    def test_extracts_formatted_replies_and_deduplicates_pairs(self):
        export = {"id": 42, "messages": [
            message(1, ["Кто ", {"type": "bold", "text": "ещё"}, " играет?"]),
            message(2, "Я!\n После девяти", reply_to_message_id=1),
            message(3, "я! после девяти", reply_to_message_id=1),
            message(4, "Позовите меня", reply_to_message_id=1),
        ]}
        data = prepare_training_data(export)
        self.assertEqual(data["texts"], ["кто еще играет?"] * 2)
        self.assertEqual(data["replies"], ["Я! После девяти", "Позовите меня"])
        self.assertEqual(data["source_message_ids"], [[1, 2], [1, 4]])
        self.assertEqual(data["stats"]["skipped_duplicate_pair"], 1)

    def test_rejects_missing_cross_chat_and_nontext_pairs(self):
        export = {"id": 42, "messages": [
            message(1, "Играем?"),
            message(2, "Да", reply_to_message_id=999),
            message(3, "Да", reply_to_message_id=1, reply_to_peer_id=43),
            message(4, "Смотри", photo="image.jpg"),
            message(5, "Красиво", reply_to_message_id=4),
            message(6, "Ответ", reply_to_message_id=1, forwarded_from="Someone"),
            message(7, "/help", reply_to_message_id=1),
            message(8, "👍", reply_to_message_id=1),
            dict(id=9, type="service", text="Joined", reply_to_message_id=1),
            message(10, "Да", reply_to_message_id=1, reply_to_peer_id=42),
        ]}
        data = prepare_training_data(export)
        self.assertEqual(data["replies"], ["Да"])
        self.assertEqual(data["stats"]["skipped_missing_parent"], 1)
        self.assertEqual(data["stats"]["skipped_cross_chat"], 1)

    def test_empty_export_and_length_limit(self):
        self.assertEqual(prepare_training_data({"messages": []})["texts"], [])
        export = {"messages": [
            message(1, "Long prompt"), message(2, "Yes", reply_to_message_id=1),
        ]}
        self.assertEqual(prepare_training_data(export, max_chars=5)["texts"], [])
        with self.assertRaises(ValueError):
            prepare_training_data([])


if __name__ == "__main__":
    unittest.main()
