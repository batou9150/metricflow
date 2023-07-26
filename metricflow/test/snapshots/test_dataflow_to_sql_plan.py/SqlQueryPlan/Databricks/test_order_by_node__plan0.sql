-- Order By ['ds', 'bookings']
SELECT
  subq_3.ds
  , subq_3.is_instant
  , subq_3.bookings
FROM (
  -- Compute Metrics via Expressions
  SELECT
    subq_2.ds
    , subq_2.is_instant
    , subq_2.bookings
  FROM (
    -- Aggregate Measures
    SELECT
      subq_1.ds
      , subq_1.is_instant
      , SUM(subq_1.bookings) AS bookings
    FROM (
      -- Pass Only Elements:
      --   ['bookings', 'is_instant', 'ds']
      SELECT
        subq_0.ds
        , subq_0.is_instant
        , subq_0.bookings
      FROM (
        -- Read Elements From Semantic Model 'bookings_source'
        SELECT
          1 AS bookings
          , CASE WHEN is_instant THEN 1 ELSE 0 END AS instant_bookings
          , bookings_source_src_10001.booking_value
          , bookings_source_src_10001.booking_value AS max_booking_value
          , bookings_source_src_10001.booking_value AS min_booking_value
          , bookings_source_src_10001.guest_id AS bookers
          , bookings_source_src_10001.booking_value AS average_booking_value
          , bookings_source_src_10001.booking_value AS booking_payments
          , CASE WHEN referrer_id IS NOT NULL THEN 1 ELSE 0 END AS referred_bookings
          , bookings_source_src_10001.booking_value AS median_booking_value
          , bookings_source_src_10001.booking_value AS booking_value_p99
          , bookings_source_src_10001.booking_value AS discrete_booking_value_p99
          , bookings_source_src_10001.booking_value AS approximate_continuous_booking_value_p99
          , bookings_source_src_10001.booking_value AS approximate_discrete_booking_value_p99
          , bookings_source_src_10001.is_instant
          , bookings_source_src_10001.ds
          , DATE_TRUNC('week', bookings_source_src_10001.ds) AS ds__week
          , DATE_TRUNC('month', bookings_source_src_10001.ds) AS ds__month
          , DATE_TRUNC('quarter', bookings_source_src_10001.ds) AS ds__quarter
          , DATE_TRUNC('year', bookings_source_src_10001.ds) AS ds__year
          , bookings_source_src_10001.ds_partitioned
          , DATE_TRUNC('week', bookings_source_src_10001.ds_partitioned) AS ds_partitioned__week
          , DATE_TRUNC('month', bookings_source_src_10001.ds_partitioned) AS ds_partitioned__month
          , DATE_TRUNC('quarter', bookings_source_src_10001.ds_partitioned) AS ds_partitioned__quarter
          , DATE_TRUNC('year', bookings_source_src_10001.ds_partitioned) AS ds_partitioned__year
          , bookings_source_src_10001.booking_paid_at
          , DATE_TRUNC('week', bookings_source_src_10001.booking_paid_at) AS booking_paid_at__week
          , DATE_TRUNC('month', bookings_source_src_10001.booking_paid_at) AS booking_paid_at__month
          , DATE_TRUNC('quarter', bookings_source_src_10001.booking_paid_at) AS booking_paid_at__quarter
          , DATE_TRUNC('year', bookings_source_src_10001.booking_paid_at) AS booking_paid_at__year
          , bookings_source_src_10001.listing_id AS listing
          , bookings_source_src_10001.guest_id AS guest
          , bookings_source_src_10001.host_id AS host
        FROM ***************************.fct_bookings bookings_source_src_10001
      ) subq_0
    ) subq_1
    GROUP BY
      subq_1.ds
      , subq_1.is_instant
  ) subq_2
) subq_3
ORDER BY subq_3.ds, subq_3.bookings DESC
