with bookings as (
    select * from {{ ref('stg_bookings') }}
),

spend as (
    select * from {{ ref('stg_onboard_spend') }}
),

guests as (
    select * from {{ ref('stg_guests') }}
),

guest_metrics as (
    select
        b.guest_id,
        b.brand,
        count(b.booking_id)                          as total_bookings,
        count(case when not b.is_cancelled then 1 end) as completed_voyages,
        count(case when b.is_cancelled then 1 end)   as cancelled_bookings,
        min(b.booking_date)                          as first_booking_date,
        max(b.booking_date)                          as last_booking_date,
        datediff('day', min(b.booking_date), max(b.booking_date)) as customer_tenure_days,
        sum(case when not b.is_cancelled then b.total_revenue_usd else 0 end) as total_cabin_revenue,
        avg(case when not b.is_cancelled then b.cabin_price_usd end) as avg_cabin_price,
        avg(b.booking_window_days)                   as avg_booking_window_days,
        sum(coalesce(s.total_onboard_spend_usd, 0))  as total_onboard_spend,
        sum(case when not b.is_cancelled
            then b.total_revenue_usd else 0 end)
            + sum(coalesce(s.total_onboard_spend_usd, 0)) as total_lifetime_value
    from bookings b
    left join spend s on b.booking_id = s.booking_id
    group by 1, 2
),

final as (
    select
        gm.*,
        g.first_name,
        g.last_name,
        g.country,
        g.age_group,
        g.loyalty_tier,
        case
            when gm.total_lifetime_value >= 50000 then 'Platinum'
            when gm.total_lifetime_value >= 20000 then 'Gold'
            when gm.total_lifetime_value >= 5000  then 'Silver'
            else 'Bronze'
        end                                          as ltv_segment
    from guest_metrics gm
    left join guests g on gm.guest_id = g.guest_id
)

select * from final