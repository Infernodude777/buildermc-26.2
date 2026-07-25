package net.infernodude777.buildermc.block;

import net.fabricmc.fabric.api.itemgroup.v1.ItemGroupEvents;
import net.infernodude777.buildermc.BuilderMC;
import net.minecraft.block.AbstractBlock;
import net.minecraft.block.Block;
import net.minecraft.block.Blocks;
import net.minecraft.item.BlockItem;
import net.minecraft.item.Item;
import net.minecraft.item.ItemGroups;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;

public class ModBlocks {

    // ─── Blocks ─────────────────────────────────────────────────────────────

    public static final Block BUILDERS_WORKBENCH = register(
        "builders_workbench",
        new BuildersWorkbenchBlock(
            AbstractBlock.Settings.copy(Blocks.CRAFTING_TABLE)
                .strength(2.5f, 6.0f)
        )
    );

    // ─── Registry Helpers ───────────────────────────────────────────────────

    private static Block register(String name, Block block) {
        // Register the block
        Block registeredBlock = Registry.register(Registries.BLOCK, BuilderMC.id(name), block);

        // Register the corresponding BlockItem
        Registry.register(
            Registries.ITEM,
            BuilderMC.id(name),
            new BlockItem(registeredBlock, new Item.Settings())
        );

        return registeredBlock;
    }

    public static void initialize() {
        BuilderMC.LOGGER.info("Registering {} blocks", BuilderMC.MOD_ID);
    }
}
