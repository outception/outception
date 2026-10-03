"""The same story across publishers. A canonical URL key catches the same
link under tracking parameters and mirrors; MinHash over title and teaser
catches the same story under different headlines; a borderline pair gets
one typed question through the decision chain. Clusters persist in
Postgres with a publisher count, and the lookups the envelope needs live
in Redis under `news:cluster:*`."""
