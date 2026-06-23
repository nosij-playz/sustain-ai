import asyncio
import unittest
from unittest.mock import patch

from backend.output import tts_and_sst


class TTSFallbackTests(unittest.TestCase):
    @patch("backend.output.tts_and_sst.edge_tts.Communicate")
    def test_generate_tts_file_returns_none_on_error(self, mock_communicate):
        mock_communicate.side_effect = RuntimeError("network down")
        self.assertIsNone(asyncio.run(tts_and_sst.generate_tts_file("hello world", "out.mp3")))


if __name__ == "__main__":
    unittest.main()
