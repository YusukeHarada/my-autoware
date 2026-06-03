from setuptools import setup

package_name = "e2e_control"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    install_requires=["setuptools", "torch", "torchvision", "opencv-python-headless"],
    entry_points={
        "console_scripts": [
            "e2e_control = e2e_control.node:main",
            "e2e_collect  = e2e_control.collect:main",
        ],
    },
)
