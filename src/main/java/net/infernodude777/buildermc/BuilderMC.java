package net.infernodude777.buildermc;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.itemgroup.v1.ItemGroupEvents;
import net.infernodude777.buildermc.block.ModBlocks;
import net.infernodude777.buildermc.item.ModItems;
import net.minecraft.item.ItemGroups;
import net.minecraft.util.Identifier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class BuilderMC implements ModInitializer {
    public static final String MOD_ID = "buildermc";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    @Override
    public void onInitialize() {
        LOGGER.info("Initializing BuilderMC - Construction tools for the modern builder!");

        // Register items and blocks
        ModItems.initialize();
        ModBlocks.initialize();

        // Add items to vanilla creative tabs
        ItemGroupEvents.modifyEntriesEvent(ItemGroups.TOOLS).register(entries -> {
            entries.add(ModItems.BUILDERS_WAND);
            entries.add(ModItems.MEASURING_TAPE);
        });

        ItemGroupEvents.modifyEntriesEvent(ItemGroups.FUNCTIONAL).register(entries -> {
            entries.add(ModBlocks.BUILDERS_WORKBENCH);
        });

        LOGGER.info("BuilderMC initialized successfully!");
    }

    public static Identifier id(String path) {
        return Identifier.of(MOD_ID, path);
    }
}
