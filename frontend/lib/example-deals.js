export const CURATED_EXAMPLE_DEAL_IDS = [
  "apple_test",
];

export function getStaticCuratedExampleDealIds() {
  return [...CURATED_EXAMPLE_DEAL_IDS];
}

export function isCuratedExampleDeal(dealId) {
  return CURATED_EXAMPLE_DEAL_IDS.includes(dealId);
}
