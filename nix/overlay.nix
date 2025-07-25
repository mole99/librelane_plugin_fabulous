new: old: {

  openroad = old.openroad.overrideAttrs (finalAttrs: previousAttrs: {
    patches = previousAttrs.patches ++ [./patches/openroad/fix_connect_by_abutment.patch];
  });

}
