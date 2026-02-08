def test_native_package_import_smoke() -> None:
    import story_gen.native as native

    assert native.__doc__ is not None
