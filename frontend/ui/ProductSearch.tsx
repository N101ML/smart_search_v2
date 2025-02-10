"use client";

import React, { useState } from "react";

interface SiteSelection {
  reddit: boolean;
  twitter: boolean;
  discord: boolean;
}

interface RetailerSelection {
  amazon: boolean;
  walmart: boolean;
  bestBuy: boolean;
}

export default function ProductSearch() {
  const [productType, setProductType] = useState<string>("");
  const [minPrice, setMinPrice] = useState<string>("");
  const [maxPrice, setMaxPrice] = useState<string>("");
  const [selectedSites, setSelectedSites] = useState<SiteSelection>({
    reddit: false,
    twitter: false,
    discord: false,
  });
  const [selectedRetailers, setSelectedRetailers] = useState<RetailerSelection>(
    {
      amazon: false,
      walmart: false,
      bestBuy: false,
    }
  );

  const [searchResponse, setSearchResponse] = useState<any>(null); // State to hold the response

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const searchData = {
      product_category: productType,
      min_price: parseFloat(minPrice),
      max_price: parseFloat(maxPrice),
      sites: (Object.keys(selectedSites) as (keyof SiteSelection)[]).filter(
        (site) => selectedSites[site]
      ),
      retailers: (
        Object.keys(selectedRetailers) as (keyof RetailerSelection)[]
      ).filter((retailer) => selectedRetailers[retailer]),
    };

    try {
      const response = await fetch("http://localhost:8000/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(searchData),
      });

      if (!response.ok) throw new Error("Search Failed");
      const data = await response.json();
      setSearchResponse(data);
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const handleSiteChange =
    (site: keyof SiteSelection) => (e: React.ChangeEvent<HTMLInputElement>) => {
      setSelectedSites((prev) => ({ ...prev, [site]: e.target.checked }));
    };

  const handleRetailerChange =
    (retailer: keyof RetailerSelection) =>
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setSelectedRetailers((prev) => ({
        ...prev,
        [retailer]: e.target.checked,
      }));
    };

  return (
    <div>
      <form
        onSubmit={handleSubmit}
        className="d-flex flex-column justify-content-center align-items-center text-start"
      >
        <div className="mb-2 w-100" style={{ maxWidth: "300px" }}>
          <label htmlFor="productType" className="form-label">
            Product Category
          </label>
          <input
            className="form-control"
            id="productType"
            placeholder="Enter a product category"
            value={productType}
            onChange={(e) => setProductType(e.target.value)}
          />
        </div>

        <div className="mb-2 w-100" style={{ maxWidth: "300px" }}>
          <label htmlFor="minPrice" className="form-label">
            Price Range
          </label>
          <div className="d-flex">
            <input
              className="form-control me-2"
              placeholder="Min price"
              value={minPrice}
              onChange={(e) => setMinPrice(e.target.value)}
            />
            <input
              className="form-control"
              placeholder="Max price"
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
            />
          </div>
        </div>

        <div className="mb-2 w-100" style={{ maxWidth: "300px" }}>
          <label htmlFor="sitesToSearch" className="form-label">
            Sites to search
          </label>
          <div className="d-flex justify-content-between">
            {["reddit", "twitter", "discord"].map((site) => (
              <div key={site}>
                <input
                  type="checkbox"
                  className="btn-check"
                  id={site}
                  checked={selectedSites[site as keyof SiteSelection]}
                  onChange={handleSiteChange(site as keyof SiteSelection)}
                />
                <label className="btn btn-outline-primary" htmlFor={site}>
                  {site}
                </label>
              </div>
            ))}
          </div>
        </div>

        <div className="mb-2 w-100" style={{ maxWidth: "300px" }}>
          <label htmlFor="retailers" className="form-label">
            Pick a retailer
          </label>
          <div className="d-flex justify-content-between">
            {["amazon", "walmart", "bestBuy"].map((retailer) => (
              <div key={retailer}>
                <input
                  type="checkbox"
                  className="btn-check"
                  id={retailer}
                  checked={
                    selectedRetailers[retailer as keyof RetailerSelection]
                  }
                  onChange={handleRetailerChange(
                    retailer as keyof RetailerSelection
                  )}
                />
                <label
                  className="btn btn-outline-primary text-capitalize"
                  htmlFor={retailer}
                >
                  {retailer.replace("bestBuy", "Best Buy")}
                </label>
              </div>
            ))}
          </div>
        </div>

        <div className="mb-2 w-100" style={{ maxWidth: "300px" }}>
          <button className="btn btn-outline-success w-100" type="submit">
            Search
          </button>
        </div>
      </form>

      {searchResponse && (
        <div>
          <h2>Search Results:</h2>
          <pre>{JSON.stringify(searchResponse, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
