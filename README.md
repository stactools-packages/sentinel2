# stactools-sentinel2

stactools package for Sentinel-2 data.

## Running

```shell
pip install stactools-sentinel2
````

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
      https://roda.sentinel-hub.com/sentinel-s2-l1c/tiles/34/L/BP/2022/4/1/0/ output
````

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
pip install -e .
```

Run the tests with:

```commandline
pytest -vvv
```

If you change the STAC metadata output, you will need to re-create the test files with the following command:

```shell
python scripts/create_expected.py
```
