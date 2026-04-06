with pricing as (
    select * from {{ ref('stg_pricing_log') }}
),

bookings as (
    select
        itinerary_name,
        brand,
        cabin_category,
        sail_date,
        avg(cabin_price_usd) as avg_booked_price
    from {{ ref('stg_bookings') }}
    where not is_cancelled
    group by 1,2,3,4
),

summary as (
    select
        p.brand,
        p.itinerary_name,
        p.region,
        p.cabin_category,
        p.sail_date,
        date_trunc('month', p.sail_date)    as sail_month,
        year(p.sail_date)                   as sail_year,
        p.price_usd                         as listed_price_usd,
        b.avg_booked_price                  as avg_booked_price_usd,
        round(
            (b.avg_booked_price - p.price_usd)
            / nullif(p.price_usd, 0) * 100, 2
        )                                   as price_variance_pct,
        case
            when b.avg_booked_price > p.price_usd * 1.05 then 'Above List'
            when b.avg_booked_price < p.price_usd * 0.95 then 'Below List'
            else 'At List'
        end                                 as price_position
    from pricing p
    left join bookings b
        on  p.itinerary_name = b.itinerary_name
        and p.brand          = b.brand
        and p.cabin_category = b.cabin_category
        and p.sail_date      = b.sail_date
)

select * from summary