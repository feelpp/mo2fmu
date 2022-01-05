from setuptools import setup

setup(
    name="mo2fmu",
    version="1.0",
    py_modules=["mo2fmu"],
    scripts=['mo2fmu'],
    include_package_data=True,
    install_requires=["click","spdlog","xvfbwrapper","pathlib"],
    entry_points="""

    """,
)
