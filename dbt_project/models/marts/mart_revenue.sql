with bookings as (
    select * from {{ ref('stg_bookings') }}
),

spend as (
    select * from {{ ref('stg_onboard_spend') }}
),

joined as (
    select
        b.booking_id,
        b.guest_id,
        b.brand,
        b.ship_name,
        b.itinerary_name,
        b.region,
        b.nights,
        b.cabin_category,
        b.num_guests,
        b.booking_date,
        b.sail_date,
        b.booking_window_days,
        b.cabin_price_usd,
        b.total_revenue_usd,
        b.booking_channel,
        b.is_cancelled,
        b.cancellation_reason,
        b.loyalty_tier,
        coalesce(s.total_onboard_spend_usd, 0) as total_onboard_spend_usd,
        coalesce(s.dining, 0)                   as dining_spend,
        coalesce(s.spa, 0)                      as spa_spend,
        coalesce(s.excursions, 0)               as excursions_spend,
        coalesce(s.beverage, 0)                 as beverage_spend,
        coalesce(s.casino, 0)                   as casino_spend,
        coalesce(s.retail, 0)                   as retail_spend,
        b.total_revenue_usd + coalesce(s.total_onboard_spend_usd, 0) as total_guest_value_usd,
        b.total_revenue_usd / nullif(b.nights, 0) as revenue_per_night_usd,
        (b.total_revenue_usd + coalesce(s.total_onboard_spend_usd, 0))
            / nullif(b.nights, 0)               as total_value_per_night_usd
    from bookings b
    left join spend s on b.booking_id = s.booking_id
)

select * from joined