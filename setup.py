from setuptools import setup, find_packages


setup(
    name="django-mailer",
    version=__import__("mailer").__version__,
    description="A reusable Django app for queuing the sending of email",
    long_description=open("docs/usage.txt").read(),
    author="James Tauber",
    author_email="jtauber@jtauber.com",
    license="MIT",
    url="https://github.com/pinax/django-mailer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Framework :: Django",
    ],
    zip_safe=False,
    install_requires=[
        'lockfile==0.9.1',
    ],
)
