# why Euro Short-Term Rate vs bonds?
## 1. The Fragmentation Problem (The Eurozone Specifics)
Unlike the United States—where there is only one "US Treasury" market—the Eurozone does not have a single unified government bond. Instead, you have individual national bonds
## 2. Supply, Demand, and Scarcity "Noise"
Government bond yields do not just move based on central bank interest rate expectations; they are highly sensitive to systemic supply and demand imbalances (BlueGamma, 2025):

Flight to Safety: During times of geopolitical or economic stress, institutional money floods into German Bunds. This massive buying pressure artificially spikes bond prices and depresses bond yields close to zero (or even negative).

Collateral Scarcity: Large institutions frequently lock up government bonds to use as regulatory collateral, creating a structural shortage.
## 3. The "Cost of Funding" Alignment
Options are packaged, sold, and hedged primarily by market makers (large investment banks). When a market maker sells you a call option, they must dynamically buy underlying stock to hedge their risk. To buy that stock, they have to borrow cash overnight.

The rate at which banks borrow cash overnight from each other is directly tied to €STR (European Central Bank, 2026).

The rate at which banks hedge interest rate risk over time is the OIS Swap market (which compounds €STR) (BlueGamma, 2025).

Because €STR tracks the actual, real-world cost of funding an institutional options portfolio, it is the only mathematically sound input to use (Azzone & Baviera, 2021). If a desk priced options using government bond yields instead, an external arbitrageur could easily exploit the pricing spread between the bond market and the actual cash funding market (Azzone & Baviera, 2021).