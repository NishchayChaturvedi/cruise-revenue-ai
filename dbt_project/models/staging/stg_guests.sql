with source as (
    select * from {{ source('raw', 'STG_GUESTS') }}
),

renamed as (
    select
        guest_id,
        first_name,
        last_name,
        email,
        country,
        age_group,
        primary_brand,
        total_bookings,
        loyalty_tier,
        _fivetran_synced::timestamp as _fivetran_synced
    from source
)

select * from renamed