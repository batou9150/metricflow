-- Combine Metrics
SELECT
  COALESCE(subq_22.metric_time, subq_23.metric_time) AS metric_time
  , subq_22.bookings AS bookings
  , subq_23.booking_payments AS booking_payments
FROM (
  -- Aggregate Measures
  -- Compute Metrics via Expressions
  SELECT
    metric_time
    , SUM(bookings) AS bookings
  FROM (
    -- Read Elements From Data Source 'bookings_source'
    -- Pass Only Additive Measures
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
  ) subq_15
  GROUP BY
    metric_time
) subq_22
FULL OUTER JOIN (
  -- Read Elements From Data Source 'bookings_source'
  -- Pass Only Additive Measures
  -- Metric Time Dimension 'booking_paid_at'
  -- Pass Only Elements:
  --   ['booking_payments', 'metric_time']
  -- Aggregate Measures
  -- Compute Metrics via Expressions
  SELECT
    booking_paid_at AS metric_time
    , SUM(booking_value) AS booking_payments
  FROM (
    -- User Defined SQL Query
    SELECT * FROM ***************************.fct_bookings
  ) bookings_source_src_10001
  GROUP BY
    metric_time
) subq_23
ON
  subq_22.metric_time = subq_23.metric_time