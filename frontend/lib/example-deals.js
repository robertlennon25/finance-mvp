export const CURATED_EXAMPLE_DEAL_IDS = [
  "apple_test",
];

export function isCuratedExampleDeal(dealId) {
  return CURATED_EXAMPLE_DEAL_IDS.includes(dealId);
}
