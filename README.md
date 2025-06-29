# stactools-sentinel2

stactools package for Sentinel-2 data.

## Examples

- [L1C item](./examples/sentinel2-l1c-example/S2A_T01LAC_20200717T221944_L1C/S2A_T01LAC_20200717T221944_L1C.json)
- [L2A item](./examples/sentinel2-l2a-example/S2A_T07HFE_20190212T192646_L2A/S2A_T07HFE_20190212T192646_L2A.json)

## Running

```shell
pip install stactools-sentinel2
```

SAFE archive:

```shell
stac sentinel2 create-item tests/data-files/S2A_MSIL2A_20190212T192651_N0212_R013_T07HFE_20201007T160857.SAFE output/
```

AWS Open Data bucket `sentinel-s2-l2a`:

```shell
stac sentinel2 create-item tests/data-files/S2A_OPER_MSI_L2A_TL_SGS__20181231T210250_A018414_T10SDG output/
```

Sentinel Hub metadata:

```shell
stac sentinel2 create-item --asset-href-prefix s3://sentinel-s2-l2a/tiles/34/L/BP/2022/4/1/0/ \
      https://roda.sentinel-hub.com/sentinel-s2-l2a/tiles/34/L/BP/2022/4/1/0/ output
```

**Note:** this does not currently work with S3 buckets using requester-pays.

The flag `--tolerance` can be set to a decimal value to define the simplification tolerance of the Item geometry.
This is a pass-through to the [Shapely simplify method](https://shapely.readthedocs.io/en/stable/manual.html#object.simplify).

## Development

Install pre-commit hooks with:

```commandline
pre-commit install
```

Run these pre-commit hooks with:

```commandline
pre-commit run --all-files
```

Install the code in the local python env so your IDE can see it:

```commandline
pip install -e ".[dev]"
```

### Testing

Run the tests with:

```commandline
pytest -vvv
```


Most tests fixture expectations can be updated by running:

```shell
pytest --update-expectations
```

If the expectation file is missing for any test in `test_commands` it will be
generated, and the test will fail.  This failure is to ensure fixture updates
don't happen silently.

Alternatively, tests can be updated by using the following command:

```shell
python scripts/create_expected.py
```
