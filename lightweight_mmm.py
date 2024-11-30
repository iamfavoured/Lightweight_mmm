# -*- coding: utf-8 -*-
"""Lightweight MMM

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1pln0ahwnvqmAPLjD-hLP0iRKlu-fBL1v
"""

# First would be to install lightweight_mmm
!pip install --upgrade git+https://github.com/google/lightweight_mmm.git
#!pip uninstall -y matplotlib
#!pip install matplotlib==3.1.3

# Import jax.numpy and any other library we might need.
import jax.numpy as jnp
import numpyro
import pandas as pd

# Import the relevant modules of the library
from lightweight_mmm import lightweight_mmm
from lightweight_mmm import optimize_media
from lightweight_mmm import plot
from lightweight_mmm import preprocessing
from lightweight_mmm import utils

"""## Organising the data for modelling"""

#csv="/content/bike_sales_data.csv"
#df=pd.read_csv(csv) #, index_col=0)
#df

df = pd.read_csv('/content/bike_sales_data.csv')

df.head()

media_data = df[['branded_search_spend', 'nonbranded_search_spend','facebook_spend', 'print_spend', 'ooh_spend','tv_spend', 'radio_spend']].to_numpy()
target = df[['sales']].to_numpy()
costs = df[['branded_search_spend', 'nonbranded_search_spend','facebook_spend', 'print_spend', 'ooh_spend','tv_spend', 'radio_spend']].sum().to_numpy()

data_size = media_data.shape[0]

# Split and scale data.
split_point = data_size - 30
# Media data
media_data_train = media_data[:split_point, ...]
media_data_test = media_data[split_point:, ...]
# Target
target_train = target[:split_point].reshape(-1)

media_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)
target_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)
cost_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)

media_data_train = media_scaler.fit_transform(media_data_train)
target_train = target_scaler.fit_transform(target_train)
costs2 = cost_scaler.fit_transform(costs)

mmm = lightweight_mmm.LightweightMMM(model_name="carryover")

number_warmup=100
number_samples=100

mmm.fit(
    media=media_data_train,
    media_prior=costs2,
    target=target_train,
    number_warmup=number_warmup,
    number_samples=number_samples,
    number_chains=1,
    )

mmm.print_summary()

plot.plot_media_channel_posteriors(media_mix_model=mmm)

plot.plot_model_fit(mmm, target_scaler=target_scaler)

# We have to scale the test media data if we have not done so before.
new_predictions = mmm.predict(media=media_scaler.transform(media_data_test))
new_predictions.shape

plot.plot_out_of_sample_model_fit(out_of_sample_predictions=new_predictions,
                                 out_of_sample_target=target_scaler.transform(target[split_point:].squeeze()))

"""### Media insights"""

media_contribution, roi_hat = mmm.get_posterior_metrics(target_scaler=target_scaler, cost_scaler=cost_scaler)

from matplotlib import pyplot as plt
import numpy as np

def custom_plot_media_baseline_contribution_area_plot(
        media_mix_model,
        target_scaler=None,
        channel_names=None,
        fig_size = (20, 7)):
      """Plots an area chart to visualize weekly media & baseline contribution.

      Args:
        media_mix_model: Media mix model.
        target_scaler: Scaler used for scaling the target.
        channel_names: Names of media channels.
        fig_size: Size of the figure to plot as used by matplotlib.

      Returns:
        Stacked area chart of weekly baseline & media contribution.
      """
      # Create media channels & baseline contribution dataframe.
      contribution_df = plot.create_media_baseline_contribution_df(
          media_mix_model=media_mix_model,
          target_scaler=target_scaler,
          channel_names=channel_names)
      contribution_df = contribution_df.clip(0)

      # Create contribution dataframe for the plot.
      contribution_columns = [
          col for col in contribution_df.columns if "contribution" in col
      ]
      contribution_df_for_plot = contribution_df.loc[:, contribution_columns]
      contribution_df_for_plot = contribution_df_for_plot[
          contribution_df_for_plot.columns[::-1]]
      period = np.arange(1, contribution_df_for_plot.shape[0] + 1)
      contribution_df_for_plot.loc[:, "period"] = period

      # Plot the stacked area chart.
      fig, ax = plt.subplots()
      contribution_df_for_plot.plot.area(
          x="period", stacked=True, figsize=fig_size, ax=ax)
      ax.set_title("Attribution Over Time", fontsize="x-large")
      ax.tick_params(axis="y")
      ax.set_ylabel("Baseline & Media Chanels Attribution")
      ax.set_xlabel("Period")
      ax.set_xlim(1, contribution_df_for_plot["period"].max())
      ax.set_xticks(contribution_df_for_plot["period"])
      ax.set_xticklabels(contribution_df_for_plot["period"])
      for tick in ax.get_xticklabels():
        tick.set_rotation(45)
      plt.close()
      return fig

custom_plot_media_baseline_contribution_area_plot(media_mix_model=mmm,
                                                target_scaler=target_scaler,
                                                fig_size=(30,10))

plot.plot_bars_media_metrics(metric=media_contribution, metric_name="Media Contribution Percentage")

plot.plot_bars_media_metrics(metric=roi_hat, metric_name="ROI hat")

plot.plot_response_curves(
    media_mix_model=mmm, target_scaler=target_scaler)

"""# Optimization"""

prices = jnp.ones(mmm.n_media_channels)

n_time_periods = 10
budget = jnp.sum(jnp.dot(prices, media_data.mean(axis=0)))* n_time_periods

# Run optimization with the parameters of choice.
solution, kpi_without_optim, previous_budget_allocation = optimize_media.find_optimal_budgets(
    n_time_periods=n_time_periods,
    media_mix_model=mmm,
    budget=budget,
    prices=prices,
    media_scaler=media_scaler,
    target_scaler=target_scaler)

# Obtain the optimal weekly allocation.
optimal_buget_allocation = prices * solution.x
optimal_buget_allocation

"""## We can plot the following:
1. Pre post optimization budget allocation comparison for each channel
2. Pre post optimization predicted target variable comparison
"""

# Plot out pre post optimization budget allocation and predicted target variable comparison.
plot.plot_pre_post_budget_allocation_comparison(media_mix_model=mmm,
                                                kpi_with_optim=solution['fun'],
                                                kpi_without_optim=kpi_without_optim,
                                                optimal_buget_allocation=optimal_buget_allocation,
                                                previous_budget_allocation=previous_budget_allocation,
                                                figure_size=(10,10))

# Let's assume we have the following datasets with the following shapes (we use

media_data, extra_features, target, costs = utils.simulate_dummy_data(
    data_size=160,
    n_media_channels=3,
    n_extra_features=2,
    geos=5) # Or geos=1 for national model

data_size=160

# Simple split of the data based on time.
split_point = data_size - data_size // 10
media_data_train = media_data[:split_point, :]
target_train = target[:split_point]
extra_features_train = extra_features[:split_point, :]
extra_features_test = extra_features[split_point:, :]

# Scale data
media_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)
extra_features_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)
target_scaler = preprocessing.CustomScaler(
    divide_operation=jnp.mean)
# scale cost up by N since fit() will divide it by number of time periods
cost_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)

media_data_train = media_scaler.fit_transform(media_data_train)
extra_features_train = extra_features_scaler.fit_transform(
    extra_features_train)
target_train = target_scaler.fit_transform(target_train)
costs = cost_scaler.fit_transform(costs)

# Fit model.
mmm = lightweight_mmm.LightweightMMM()
mmm.fit(media=media_data,
        extra_features=extra_features,
        media_prior=costs,
        target=target,
        number_warmup=1000,
        number_samples=1000,
        number_chains=2)

# See detailed explanation on custom priors in our documentation.
custom_priors = {"intercept": numpyro.distributions.Uniform(1, 5)}

# Fit model.
mmm = lightweight_mmm.LightweightMMM()
mmm.fit(media=media_data,
        extra_features=extra_features,
        media_prior=costs,
        target=target,
        number_warmup=1000,
        number_samples=1000,
        number_chains=2,
        custom_priors=custom_priors)

mmm.print_summary()

plot.plot_media_channel_posteriors(media_mix_model=mmm,)

"""## New Trial"""

adstock_models = ["adstock", "hill_adstock", "carryover"]
degrees_season = [1,2,3]

adstock_models = ["hill_adstock"]
degrees_season = [1]


for model_name in adstock_models:
for degrees in degrees_season:
    mmm = lightweight_mmm.LightweightMMM(model_name=model_name)
    mmm.fit(media=media_data_train_scaled,
            media_prior=costs_scaled,
            target=target_train_scaled,
            extra_features=organic_data_train_scaled,
            number_warmup=1000,
            number_samples=1000,
            number_chains=1,
            degrees_seasonality=degrees,
            weekday_seasonality=True,
            seasonality_frequency=365,
            seed=1)

    prediction = mmm.predict(
    media=media_data_test_scaled,
    extra_features=organic_data_test_scaled,
    target_scaler=target_scaler)
    p = prediction.mean(axis=0)

    mape = mean_absolute_percentage_error(target_test.values, p)
    print(f"model_name={model_name} degrees={degrees} MAPE={mape} samples={p[:3]}")

