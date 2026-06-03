from setuptools import setup

package_name = "speed_monitor"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    install_requires=["setuptools"],
    entry_points={
        "console_scripts": [
            "speed_monitor = speed_monitor.node:main",
        ],
    },
)
