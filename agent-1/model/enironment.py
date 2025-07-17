# import pydantic
import shapely


class Wall:
    """Depicts walls, that agents cannot pass through

    Args:
        area (list[tuple[int, int], ...]): list of pairs coordinate pairs of a polygon corners
        enclosed (bool, optional): Descirbes whether the last point connects to the star or not. Defaults to True.
    """

    def __init__(
        self,
        area: list[tuple[int, int], ...],
        enclosed: bool = True,
    ):
        if enclosed:
            area.append(area[0])
        self.__borders = zip(*area)

    @property
    def borders(self):
        return self.__borders


# Import libraries
# import matplotlib.pyplot as plt
# from mpl_toolkits.mplot3d import Axes3D
# import numpy as np


# # Create axis
# axes = [5, 5, 5]

# # Create Data
# data = np.ones(axes, dtype=np.bool)

# # Control Transparency
# alpha = 0.9

# # Control colour
# colors = np.empty(axes + [4], dtype=np.float32)

# colors[:] = [1, 0, 0, alpha]  # red

# # Plot figure
# fig = plt.figure()
# ax = fig.add_subplot(111, projection="3d")

# # Voxels is used to customizations of the
# # sizes, positions and colors.
# ax.voxels(data, facecolors=colors)

# fig.show()
# input()
# fig.close()
