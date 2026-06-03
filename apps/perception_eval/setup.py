from setuptools import setup

setup(
    name="perception_eval",
    version="0.1.0",
    packages=["perception_eval"],
    install_requires=["setuptools"],
    entry_points={
        "console_scripts": [
            "perception_eval = perception_eval.node:main",
        ],
    },
)
