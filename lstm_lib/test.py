from learningwr import resample_dataset
import numpy as np


loaded_data = np.load("datasets.npz")
x = loaded_data["x"]
y = loaded_data["y"]

x_train_std, y_train = resample_dataset(x, y, [0,0.5,1], "up")
