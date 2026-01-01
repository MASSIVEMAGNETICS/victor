import h5py
import torch
import numpy as np
import json
from typing import Dict, Any, List

class DatasetLoader:
    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path
        self.file = None
        self._open_file()

    def _open_file(self):
        """Open dataset file."""
        self.file = h5py.File(self.dataset_path, 'r')

    def get_sample_count(self) -> int:
        """Get total number of samples in dataset."""
        return len(self.file['text'])

    def load_sample(self, idx: int) -> Dict[str, Any]:
        """Load single sample by index."""
        # Note: h5py reading is generally thread-safe for reads,
        # but better to open locally if threading is heavy.
        # For this implementation we use the shared handle.
        key = f'sample_{idx}'
        text = self.file['text'][key][()].decode('utf-8')
        image = self.file['images'][key][()]
        reasoning_str = self.file['reasoning'][key][()].decode('utf-8')
        reasoning = json.loads(reasoning_str)

        entropy = self.file['text'][key].attrs['entropy']
        depth_hint = self.file['text'][key].attrs['depth_hint']

        return {
            'text': text,
            'image': torch.from_numpy(image).permute(2, 0, 1).float() / 255.0,
            'reasoning': reasoning,
            'entropy': float(entropy),
            'depth_hint': int(depth_hint)
        }

    def __del__(self):
        """Close file on deletion."""
        if self.file:
            self.file.close()
