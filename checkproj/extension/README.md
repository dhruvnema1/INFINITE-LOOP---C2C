# Extension

Load this folder as an unpacked Chrome extension.

The extension intentionally has no seeded scan response. Popup results are
created from the current tab's extracted content and the local AI API response.

The extension does not bundle the training CSV or model. The model is produced
by `training/train_model.py` and remains on the Python backend.
