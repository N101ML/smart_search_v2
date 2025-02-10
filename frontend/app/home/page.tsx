import ProductSearch from "@/ui/ProductSearch";

export default function Home() {
  return (
    <div className="container text-center">
      <div className="row">
        <h1>SmartSearch</h1>
      </div>
      <div className="row">
        <ProductSearch />
      </div>
    </div>
  );
}
