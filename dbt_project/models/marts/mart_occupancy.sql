with bookings as (
    select * from {{ ref('stg_bookings') }}
),

occupancy as (
    select
        brand,
        ship_name,
        itinerary_name,
        region,
        sail_date,
        month(sail_date)          as sail_month,
        quarter(sail_date)        as sail_quarter,
        year(sail_date)                         as sail_year,
        count(booking_id)                       as total_bookings,
        count(case when not is_cancelled then 1 end) as confirmed_bookings,
        count(case when is_cancelled then 1 end)     as cancelled_bookings,
        sum(case when not is_cancelled then num_guests else 0 end) as total_guests,
        round(
            count(case when not is_cancelled then 1 end) * 100.0
            / nullif(count(booking_id), 0), 2
        )                                       as occupancy_rate_pct,
        round(
            count(case when is_cancelled then 1 end) * 100.0
            / nullif(count(booking_id), 0), 2
        )                                       as cancellation_rate_pct,
        avg(booking_window_days)                as avg_booking_window_days,
        avg(cabin_price_usd)                    as avg_cabin_price_usd,
        sum(case when not is_cancelled then total_revenue_usd else 0 end) as total_revenue_usd
    from bookings
    group by 1,2,3,4,5,6,7,8
)

select * from occupancy