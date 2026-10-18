# V2.24 — One-row collection controls

Payment promises is now **Promises** and Collections run history is **Run history**. Together with Run collections and Run overview, the four controls stay in one row.

The desktop toolbar takes the width its contents need instead of a 55vw allocation, and its controls no longer wrap or shrink. On narrow screens (<=760px), the same row scrolls horizontally so labels remain readable. Existing right alignment, counters, menu actions and viewport-clamped panels remain.

Merge, deploy and hard-refresh. App v2.24 / UI workflow-24 identify this build. No new SQL, environment values, dependencies, quota changes or model/email calls. SQL017 remains a prerequisite only for the earlier Edit draft feature.

Validation: inspected the supplied screenshot; checked all four controls/short labels, intrinsic width/nowrap rules, narrow-screen scrolling, six script cache versions, preserved analytics beacon and Python compilation. Existing seven mocked popover geometry cases passed. Native browser pixel/zoom acceptance remains the owner's post-deploy check. No live database changes or deployment performed.
