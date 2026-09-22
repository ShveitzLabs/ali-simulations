# ALI Simulations v0.7.2 — React Effect Hotfix

Fixes the two remaining TypeScript errors in the v0.7 Belonging frontend.

Root cause: the Network and Belonging components passed their async-returning `load`
function directly to `useEffect` (`useEffect(load, [])`). React EffectCallback must return
void or a cleanup function, not a Promise.

Changed both to a void-returning effect wrapper:
`useEffect(() => { void load(); }, [])`

No database or migration changes.
