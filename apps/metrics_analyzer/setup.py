from setuptools import setup

setup(
    name="metrics_analyzer",
    version="0.1.0",
    packages=["metrics_analyzer"],
    install_requires=["matplotlib"],
    entry_points={
        "console_scripts": [
            "metrics_analyze = metrics_analyzer.analyze:run",
        ],
    },
)
