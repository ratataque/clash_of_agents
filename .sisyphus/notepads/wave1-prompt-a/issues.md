## Issues

- Runtime behavior still returns `status="Reject"` for Test P despite prompt override text updates; likely indicates stronger competing instructions or model policy weighting requiring additional prompt disambiguation.
- Current Test P runtime message still suggests alternative products in the unavailable scenario, which conflicts with the new no-substitutes requirement for this special case.
