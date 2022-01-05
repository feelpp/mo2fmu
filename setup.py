from setuptools import setup

setup(
    name="mo2fmu",
    version="2.0",
    py_modules=["mo2fmu"],
    include_package_data=True,
    install_requires=["click","spdlog","xvfbwrapper","platform","pathlib"],
    entry_points="""

    """,
)
