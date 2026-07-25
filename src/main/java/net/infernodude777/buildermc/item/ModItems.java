package net.infernodude777.buildermc.item;

import net.fabricmc.fabric.api.itemgroup.v1.FabricItemGroupEntries;
import net.infernodude777.buildermc.BuilderMC;
import net.minecraft.item.Item;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.util.Rarity;

public class ModItems {

    // ─── Items ──────────────────────────────────────────────────────────────

    public static final Item BUILDERS_WAND = register(
        "builders_wand",
        new BuildersWandItem(new Item.Settings()
            .maxCount(1)
            .rarity(Rarity.UNCOMMON)
            .fireproof()
        )
    );

    public static final Item MEASURING_TAPE = register(
        "measuring_tape",
        new MeasuringTapeItem(new Item.Settings()
            .maxCount(1)
            .rarity(Rarity.COMMON)
        )
    );

    // ─── Registry Helper ────────────────────────────────────────────────────

    private static Item register(String name, Item item) {
        return Registry.register(Registries.ITEM, BuilderMC.id(name), item);
    }

    public static void initialize() {
        // Static initializer forces class loading and registry entries
        BuilderMC.LOGGER.info("Registering {} items", BuilderMC.MOD_ID);
    }
}
