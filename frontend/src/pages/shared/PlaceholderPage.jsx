import Icon from "../../components/Icon";
import { PageHeading } from "./WorkspaceTools";

const modules = {
  Suppliers: {
    icon: "suppliers",
    tone: "info",
    description: "Supplier management is planned for this workspace.",
  },
  Transactions: {
    icon: "transactions",
    tone: "success",
    description: "Inventory transaction management is planned for this workspace.",
  },
};

export default function PlaceholderPage({ title }) {
  const { icon, tone, description } = modules[title];

  return (
    <div className="workspace-page">
      <PageHeading title={title} />
      <section className="ui-card workspace-placeholder" aria-labelledby="module-status">
        <div className="workspace-placeholder-copy">
          <h2 id="module-status">Module pending</h2>
          <p>{description}</p>
        </div>
        <div className={`workspace-placeholder-mark ui-tone-${tone}`} aria-hidden="true">
          <span><Icon name={icon} /></span>
        </div>
      </section>
    </div>
  );
}
