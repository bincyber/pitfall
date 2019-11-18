
install:
	pipenv sync --dev

clean:
	find . -name "*pyc" -exec rm -f "{}" \;
	find . -name "__pycache__" -exec rm -rf "{}" \;
	rm -rf /tmp/.pulumi ./pitf-* ./htmlcov .coverage coverage.xml .mypy_cache .eggs pitfall.egg-info build dist

test:
	nose2 -v -s tests/ --with-coverage --coverage-report html
	coverage report

e2e-test-aws:
	nose2 -v -s e2e/aws

e2e-test-localstack:
	docker container inspect localstack &>/dev/null || make run-localstack
	nose2 -v -s e2e/localstack

lint:
	flake8 --statistics pitfall/* tests/* e2e/*

scan:
	bandit -r pitfall/

static-analysis:
	mypy pitfall/*

run-localstack:
	docker run -d -e "HOSTNAME=localhost" -e "SERVICES=s3" -p 4572:4572 --name "localstack" localstack/localstack:0.10.3

package:
	python setup.py sdist bdist_wheel

publish:
	twine upload dist/*
