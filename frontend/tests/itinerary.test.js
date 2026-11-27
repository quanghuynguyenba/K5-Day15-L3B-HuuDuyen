import assert from "node:assert/strict";
import test from "node:test";
import {
  formatMoney,
  hasCoordinates,
  overviewPoints,
  routePoints,
} from "../src/utils/itinerary.js";
import { desktopDensity } from "../src/hooks/useDesktopDensity.js";

test("missing or malformed prices are never presented as free admission", () => {
  assert.equal(formatMoney(0), "0đ");
  for (const price of [null, undefined, NaN, Infinity, "70000"]) {
    assert.equal(formatMoney(price), "Chưa có chi phí");
  }
  assert.equal(formatMoney(70000), "70.000đ");
});

test("invalid coordinates are excluded while zero coordinates remain valid", () => {
  assert.equal(hasCoordinates({ lat: 0, lng: 0 }), true);
  for (const point of [
    { lat: null, lng: 105 },
    { lat: 91, lng: 105 },
    { lat: 21, lng: 181 },
    { lat: NaN, lng: 105 },
  ]) {
    assert.equal(hasCoordinates(point), false);
  }
});

test("route overview includes stops missing from geometry and ignores invalid points", () => {
  const plan = {
    polyline: [[21, 105], null, [999, 105]],
    stops: [
      { lat: 22, lng: 106 },
      { lat: null, lng: 105 },
    ],
  };
  assert.deepEqual(routePoints(plan), [[21, 105]]);
  assert.deepEqual(overviewPoints(plan), [
    [21, 105],
    [22, 106],
  ]);
  assert.deepEqual(overviewPoints(null), []);
});

test("desktop density stays bounded and does not shrink tablet or mobile text", () => {
  assert.equal(desktopDensity(800), 1);
  assert.equal(desktopDensity(1024), 1);
  assert.equal(desktopDensity(1101), 0.8);
  assert.equal(desktopDensity(1520), 0.8);
  assert.equal(desktopDensity(1900), 1);
  assert.equal(desktopDensity(2560), 1);
});
