-- Compute Metrics via Expressions
SELECT
  metric_time
  , (bookings - bookings_2_weeks_ago) / bookings_2_weeks_ago AS bookings_growth_2_weeks
FROM (
  -- Combine Metrics
  SELECT
    COALESCE(subq_22.metric_time, subq_20.metric_time, subq_21.metric_time) AS metric_time
    , subq_20.bookings AS bookings
    , subq_21.bookings_2_weeks_ago AS bookings_2_weeks_ago
  FROM (
    -- Date Spine
    SELECT
      ds AS metric_time
    FROM ***************************.mf_time_spine subq_22
  ) subq_22
  INNER JOIN (
    -- Aggregate Measures
    -- Compute Metrics via Expressions
    SELECT
      metric_time
      , SUM(bookings) AS bookings
    FROM (
      -- Read Elements From Data Source 'bookings_source'
      -- Metric Time Dimension 'ds'
      -- Pass Only Elements:
      --   ['bookings', 'metric_time']
      SELECT
        ds AS metric_time
        , 1 AS bookings
      FROM (
        -- User Defined SQL Query
        SELECT * FROM ***************************.fct_bookings
      ) bookings_source_src_10001
    ) subq_14
    GROUP BY
      metric_time
  ) subq_20
  ON
    subq_22.metric_time = subq_20.metric_time
  INNER JOIN (
    -- Aggregate Measures
    -- Compute Metrics via Expressions
    SELECT
      metric_time
      , SUM(bookings) AS bookings_2_weeks_ago
    FROM (
      -- Read Elements From Data Source 'bookings_source'
      -- Metric Time Dimension 'ds'
      -- Pass Only Elements:
      --   ['bookings', 'metric_time']
      SELECT
        ds AS metric_time
        , 1 AS bookings
      FROM (
        -- User Defined SQL Query
        SELECT * FROM ***************************.fct_bookings
      ) bookings_source_src_10001
    ) subq_18
    GROUP BY
      metric_time
  ) subq_21
  ON
    subq_20.metric_time - INTERVAL 14 day = subq_21.metric_time
) subq_23
