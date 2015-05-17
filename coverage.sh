#!/bin/bash
rm -R htmlcov
coverage run --source=awslogs setup.py test
coverage html
