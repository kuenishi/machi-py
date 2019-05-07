from setuptools import setup, find_packages

setup(
    name="machi-store",
    version="0.0.3",
    description="Persistent Blob Store",
    author="Kota UENISHI",
    author_email="kuenishi@gmail.com",
    url="https://github.com/kuenishi/machi-py/",
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    python_requires=">=3.7",
    extras_require={"test": ["coverage", "black", "pytest", "pytest-xdist", "numpy"]},
    classifiers=[
        "Development Status :: 3 - Alpha",
        #   4 - Beta
        #   5 - Production/Stable
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
    ],
)
