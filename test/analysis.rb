# frozen_string_literal: true

require 'csv'

def expected_baseline_columns
  return [
    'building_id',
    'job_id',
    'completed_status',
    'report_simulation_output.add_timeseries_dst_column',
    'report_simulation_output.add_timeseries_utc_column',
    'report_simulation_output.energy_use_total_m_btu',
    'report_simulation_output.energy_use_net_m_btu',
    'report_simulation_output.fuel_use_electricity_total_m_btu',
    'report_simulation_output.end_use_natural_gas_heating_m_btu',
    'report_simulation_output.emissions_co_2_e_lrmer_mid_case_15_total_lb',
    'upgrade_costs.door_area_ft_2',
    'qoi_report.qoi_average_maximum_daily_timing_cooling_hour'
  ]
end

def expected_upgrade_columns
  return [
    'apply_upgrade.upgrade_name'
  ]
end

def expected_baseline_nonnull_columns
  return [
    'report_simulation_output.energy_use_net_m_btu',
    'upgrade_costs.door_area_ft_2'
  ]
end

def expected_upgrade_nonnull_columns
  return [
    'upgrade_costs.option_01_name',
    'upgrade_costs.option_01_cost_usd',
    'upgrade_costs.upgrade_cost_usd'
  ]
end

def expected_baseline_nonzero_columns
  return [
    'report_simulation_output.energy_use_total_m_btu'
  ]
end

def expected_upgrade_nonzero_columns
  return [
    'upgrade_costs.upgrade_cost_usd'
  ]
end

def expected_baseline_contents(testing)
  contents = [
    'data_point_out.json',
    'home.xml',
    'results_timeseries.csv'
  ]
  contents += [
    'existing.osw',
    'existing.xml',
    'in.osm',
    'in.idf',
    'schedules.csv'
  ] if testing
  return contents
end

def expected_upgrade_contents
  contents = [
    'upgraded.osw',
    'upgraded.xml'
  ]
  return contents
end

def expected_timeseries_columns(testing)
  contents = [
    'TimeDST',
    'TimeUTC',
    'Energy Use: Total',
    'Fuel Use: Electricity: Total',
    'End Use: Natural Gas: Heating',
    'Emissions: CO2e: LRMER_MidCase_15: Total'
  ]
  contents += [
    'Energy Use: Net',
    'Zone People Occupant Count: Living Space'
  ] if testing
  return contents
end

def _test_columns(results, upgrade = false)
  assert(!results.empty?)
  assert(_test_baseline_columns(results))
  assert(_test_upgrade_columns(results)) if upgrade
  assert(_test_nonnull_columns(results, upgrade))
  assert(_test_nonzero_columns(results, upgrade))
end

def _test_contents(contents, upgrade = false, testing = false)
  assert(_test_baseline_contents(contents, testing))
  if upgrade || !testing
    assert(_test_upgrade_contents(contents, testing))
  else # only when debug=true (i.e., testing project) are baseline contents different from upgrades contents
    assert(!_test_upgrade_contents(contents, testing))
  end
end

def _test_baseline_columns(results)
  expected_columns = expected_baseline_columns

  return true if (expected_columns - results.headers).empty?

  return false
end

def _test_upgrade_columns(results)
  expected_columns = expected_baseline_columns + expected_upgrade_columns

  return true if (expected_columns - results.headers).empty?

  return false
end

def _test_nonnull_columns(results, upgrade = false)
  expected_columns = expected_baseline_nonnull_columns
  if upgrade
    expected_columns += expected_upgrade_nonnull_columns
  end

  result = true
  expected_columns.each do |col|
    next if !results.headers.include?(col)

    result = false if results[col].all? { |i| i.nil? }
  end
  return result
end

def _test_nonzero_columns(results, upgrade = false)
  expected_columns = expected_baseline_nonzero_columns
  if upgrade
    expected_columns += expected_upgrade_nonzero_columns
  end

  result = true
  expected_columns.each do |col|
    next if !results.headers.include?(col)

    result = false if results[col].all? { |i| i == 0 }
  end
  return result
end

def _test_baseline_contents(contents, testing = false)
  expected_contents = expected_baseline_contents(testing)

  return true if (expected_contents - contents).empty?

  return false
end

def _test_upgrade_contents(contents, testing = false)
  expected_contents = expected_baseline_contents(testing)
  expected_contents += expected_upgrade_contents if testing

  return true if (expected_contents - contents).empty?

  return false
end

def _test_timeseries_columns(timeseries, testing = false)
  expected_columns = expected_timeseries_columns(testing)

  return true if (expected_columns - timeseries).empty?

  return false
end

def _get_timeseries_columns(paths)
  timeseries = []
  paths.each do |path|
    CSV.read(path, headers: true).headers.each do |header|
      timeseries << header if !timeseries.include?(header)
    end
  end
  return timeseries
end
