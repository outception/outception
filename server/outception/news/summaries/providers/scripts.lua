-- reserve: fail if any cap would be exceeded, else charge every counter in
-- one step and remember the reservation. One script so two callers racing
-- for the last units of the paid day or a consumer's share cannot both pass
-- a read-then-write check.
-- KEYS: lane_hour, lane_day, global_hour, reserve, sub_day, paid_day
--       (sub_day and paid_day are '' when they do not apply)
-- ARGV: est, lane_hour_cap, lane_day_cap, global_hour_cap, reserve_ttl,
--       hour_ttl, day_ttl, sub_cap, paid_cap
-- returns 1 on success, 0 for a lane or global cap, 2 for the consumer's
-- share, 3 for the paid day
local est = tonumber(ARGV[1])
local lane_hour = tonumber(redis.call('GET', KEYS[1]) or '0')
local lane_day = tonumber(redis.call('GET', KEYS[2]) or '0')
local global_hour = tonumber(redis.call('GET', KEYS[3]) or '0')
if lane_hour + est > tonumber(ARGV[2]) then return 0 end
if lane_day + est > tonumber(ARGV[3]) then return 0 end
if global_hour + est > tonumber(ARGV[4]) then return 0 end
local sub_key = KEYS[5]
if sub_key ~= '' then
  local sub = tonumber(redis.call('GET', sub_key) or '0')
  if sub + est > tonumber(ARGV[8]) then return 2 end
end
local paid_key = KEYS[6]
if paid_key ~= '' then
  local paid = tonumber(redis.call('GET', paid_key) or '0')
  if paid + est > tonumber(ARGV[9]) then return 3 end
end
redis.call('INCRBY', KEYS[1], est)
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[6]))
redis.call('INCRBY', KEYS[2], est)
redis.call('EXPIRE', KEYS[2], tonumber(ARGV[7]))
redis.call('INCRBY', KEYS[3], est)
redis.call('EXPIRE', KEYS[3], tonumber(ARGV[6]))
if sub_key ~= '' then
  redis.call('INCRBY', sub_key, est)
  redis.call('EXPIRE', sub_key, tonumber(ARGV[7]))
end
if paid_key ~= '' then
  redis.call('INCRBY', paid_key, est)
  redis.call('EXPIRE', paid_key, tonumber(ARGV[7]))
end
redis.call('SET', KEYS[4], est, 'EX', tonumber(ARGV[5]))
return 1
