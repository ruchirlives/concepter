import { useEffect, useMemo, useRef, useState } from "react";

const DEFAULT_LAYER_KEYS = [
  "containers",
  "relationships",
  "influence",
  "flow",
  "notes",
];

const toKey = (layer) => {
  if (!layer) {
    return undefined;
  }
  if (typeof layer === "string") {
    return layer;
  }
  if (typeof layer === "object") {
    return (
      layer.id ||
      layer.key ||
      layer.name ||
      layer.label ||
      layer.type ||
      undefined
    );
  }
  return undefined;
};

const normaliseOrdering = (orderingCandidate) => {
  if (Array.isArray(orderingCandidate)) {
    return orderingCandidate
      .map((entry) => toKey(entry))
      .filter((key) => typeof key === "string" && key.length > 0);
  }
  if (orderingCandidate && typeof orderingCandidate === "object") {
    return Object.keys(orderingCandidate);
  }
  return [];
};

const ensureAllLayersPresent = (orderingCandidate, layerKeys) => {
  const normalised = normaliseOrdering(orderingCandidate);
  const seen = new Set();
  const merged = [];

  for (const key of normalised) {
    if (layerKeys.has(key) && !seen.has(key)) {
      merged.push(key);
      seen.add(key);
    }
  }

  for (const key of layerKeys) {
    if (!seen.has(key)) {
      merged.push(key);
      seen.add(key);
    }
  }

  return merged;
};

const initialOrdering = (layerKeys, savedOrdering) => {
  const baseKeys = new Set(layerKeys);
  if (baseKeys.size === 0) {
    DEFAULT_LAYER_KEYS.forEach((key) => baseKeys.add(key));
  }
  const startingPoint = savedOrdering ?? DEFAULT_LAYER_KEYS;
  return ensureAllLayersPresent(startingPoint, baseKeys);
};

const orderingToken = (ordering) => JSON.stringify(ordering);

export default function AppLayers({
  layers = [],
  savedState,
  onOrderingChange,
}) {
  const layerKeys = useMemo(() => {
    const keys = new Set();
    for (const layer of layers) {
      const key = toKey(layer);
      if (key) {
        keys.add(key);
      }
    }
    return keys;
  }, [layers]);

  const savedOrdering = savedState?.layerOrdering;

  const [layerOrdering, setLayerOrdering] = useState(() =>
    initialOrdering(layerKeys, savedOrdering)
  );

  const lastAppliedToken = useRef(orderingToken(layerOrdering));

  useEffect(() => {
    const saved = savedOrdering ? ensureAllLayersPresent(savedOrdering, layerKeys) : null;
    const savedToken = saved ? orderingToken(saved) : null;

    if (savedToken && savedToken !== lastAppliedToken.current) {
      lastAppliedToken.current = savedToken;
      setLayerOrdering(saved);
      return;
    }

    setLayerOrdering((previous) => {
      const merged = ensureAllLayersPresent(
        previous && previous.length ? previous : DEFAULT_LAYER_KEYS,
        layerKeys
      );
      lastAppliedToken.current = orderingToken(merged);
      return merged;
    });
  }, [layerKeys, savedOrdering]);

  useEffect(() => {
    if (typeof onOrderingChange === "function") {
      onOrderingChange(layerOrdering);
    }
  }, [layerOrdering, onOrderingChange]);

  return null;
}

export { ensureAllLayersPresent };
