new: old: {

  openroad = old.openroad.overrideAttrs (finalAttrs: previousAttrs: {
    patches = previousAttrs.patches ++ [./patches/openroad/fix_connect_by_abutment.patch];
  });

  fabulous-fpga = old.fabulous-fpga.overrideAttrs (finalAttrs: previousAttrs: {
    patches = previousAttrs.patches ++ [./patches/fabulous/fix_supertile_framedata_o.patch];
  });

}
