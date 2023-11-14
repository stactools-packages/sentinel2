import unittest

from shapely.geometry import box, mapping, shape
from stactools.core.projection import reproject_shape
from stactools.sentinel2.constants import SENTINEL2_PROPERTY_PREFIX as s2_prefix
from stactools.sentinel2.granule_metadata import GranuleMetadata
from stactools.sentinel2.product_metadata import ProductMetadata
from stactools.sentinel2.safe_manifest import SafeManifest

from tests import test_data


class Sentinel2MetadataTest(unittest.TestCase):
    def test_parses_product_metadata_properties(self):
        manifest_path = test_data.get_path(
            "data-files/S2A_MSIL2A_20190212T192651_N0212_R013_T07HFE_20201007T160857.SAFE"
        )

        manifest = SafeManifest(manifest_path)

        product_metadata = ProductMetadata(manifest.product_metadata_href)
        granule_metadata = GranuleMetadata(manifest.granule_metadata_href)

        s2_props = product_metadata.metadata_dict
        s2_props.update(granule_metadata.metadata_dict)

        # fmt: off
        expected = {
            # From product metadata
            f"{s2_prefix}:product_uri":
                "S2A_MSIL2A_20190212T192651_N0212_R013_T07HFE_20201007T160857.SAFE",
            f"{s2_prefix}:generation_time": "2020-10-07T16:08:57.135Z",
            f"{s2_prefix}:processing_baseline": "02.12",
            f"{s2_prefix}:product_type": "S2MSI2A",
            f"{s2_prefix}:datatake_id": "GS2A_20190212T192651_019029_N02.12",
            f"{s2_prefix}:datatake_type": "INS-NOBS",
            f"{s2_prefix}:datastrip_id":
                "S2A_OPER_MSI_L2A_DS_ESRI_20201007T160858_S20190212T192646_N02.12",
            f"{s2_prefix}:tile_id":
                "S2A_OPER_MSI_L2A_TL_ESRI_20201007T160858_A019029_T07HFE_N02.12",
            f"{s2_prefix}:reflectance_conversion_factor": 1.02763689829235,
            # From granule metadata
            f"{s2_prefix}:degraded_msi_data_percentage": 0.0,
            f"{s2_prefix}:nodata_pixel_percentage": 96.769553,
            f"{s2_prefix}:saturated_defective_pixel_percentage": 0.0,
            f"{s2_prefix}:dark_features_percentage": 0.0,
            f"{s2_prefix}:cloud_shadow_percentage": 0.0,
            f"{s2_prefix}:vegetation_percentage": 0.000308,
            f"{s2_prefix}:not_vegetated_percentage": 0.069531,
            f"{s2_prefix}:water_percentage": 48.349833,
            f"{s2_prefix}:unclassified_percentage": 0.0,
            f"{s2_prefix}:medium_proba_clouds_percentage": 14.61311,
            f"{s2_prefix}:high_proba_clouds_percentage": 24.183494,
            f"{s2_prefix}:thin_cirrus_percentage": 12.783723,
            f"{s2_prefix}:snow_ice_percentage": 0.0,
        }
        # fmt: on

        for k, v in expected.items():
            self.assertIn(k, s2_props)
            self.assertEqual(s2_props[k], v)

        self.assertEqual(granule_metadata.cloudiness_percentage, 51.580326)
        self.assertEqual(
            granule_metadata.processing_baseline,
            s2_props[f"{s2_prefix}:processing_baseline"],
        )

    def test_footprint_containing_geom_with_z_dimension(self):
        product_md_path = test_data.get_path(
            "data-files/S2A_MSIL2A_20150826T185436_N0212_R070"
            "_T11SLT_20210412T023147/MTD_MSIL2A.xml"
        )
        granule_md_path = test_data.get_path(
            "data-files/S2A_MSIL2A_20150826T185436_N0212_R070"
            "_T11SLT_20210412T023147/MTD_TL.xml"
        )
        product_metadata = ProductMetadata(product_md_path)
        granule_metadata = GranuleMetadata(granule_md_path)

        footprint = shape(product_metadata.geometry)

        proj_bbox = granule_metadata.proj_bbox
        epsg = granule_metadata.epsg

        proj_box = box(*proj_bbox)
        ll_proj_box = shape(
            reproject_shape(f"epsg:{epsg}", "epsg:4326", mapping(proj_box))
        )

        # Test that the bboxes roughly match by ensuring the difference
        # is less than 5% of total area of the reprojected proj bbox.
        self.assertTrue(
            footprint.envelope.difference(ll_proj_box).area < (ll_proj_box.area * 0.05)
        )

    def test_footprint_containing_geom_with_0_parses(self):
        product_md_path = test_data.get_path(
            "data-files/S2A_MSIL2A_20180721T053721"
            "_N0212_R062_T43MDV_20201011T181419.SAFE/MTD_MSIL2a.xml"
        )
        product_metadata = ProductMetadata(product_md_path)

        footprint = shape(product_metadata.geometry)

        self.assertTrue(footprint.is_valid)
