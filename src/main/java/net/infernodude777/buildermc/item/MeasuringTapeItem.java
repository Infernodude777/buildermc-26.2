package net.infernodude777.buildermc.item;

import net.minecraft.component.DataComponentTypes;
import net.minecraft.component.NbtComponent;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.item.ItemUsageContext;
import net.minecraft.sound.SoundCategory;
import net.minecraft.sound.SoundEvents;
import net.minecraft.text.Text;
import net.minecraft.util.ActionResult;
import net.minecraft.util.Hand;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.World;

/**
 * Measuring Tape — right-click two points to measure the distance between them.
 *
 * First click marks Point A, second click marks Point B and shows the distance.
 * Shift-right-click to reset.
 */
public class MeasuringTapeItem extends Item {

    public MeasuringTapeItem(Settings settings) {
        super(settings);
    }

    @Override
    public ActionResult useOnBlock(ItemUsageContext context) {
        World world = context.getWorld();
        PlayerEntity player = context.getPlayer();
        BlockPos clickedPos = context.getBlockPos();
        Hand hand = context.getHand();

        if (world.isClient || player == null) {
            return ActionResult.SUCCESS;
        }

        ItemStack stack = player.getStackInHand(hand);

        // Shift-right-click to reset measurement
        if (player.isSneaking()) {
            clearMeasurement(stack, player);
            return ActionResult.SUCCESS;
        }

        // Get or set the first position
        BlockPos posA = getPosA(stack);

        if (posA == null) {
            // First click — set Point A
            setPosA(stack, clickedPos, player);
            player.sendMessage(
                Text.translatable("item.buildermc.measuring_tape.point_a",
                    clickedPos.getX(), clickedPos.getY(), clickedPos.getZ()),
                true
            );
            player.playSound(SoundEvents.BLOCK_LEVER_CLICK, SoundCategory.PLAYERS, 0.5f, 1.0f);
        } else {
            // Second click — calculate distance
            int dx = Math.abs(clickedPos.getX() - posA.getX());
            int dy = Math.abs(clickedPos.getY() - posA.getY());
            int dz = Math.abs(clickedPos.getZ() - posA.getZ());
            int blockDistance = dx + dy + dz;
            double euclideanDistance = Math.sqrt(dx * dx + dy * dy + dz * dz);

            player.sendMessage(
                Text.translatable("item.buildermc.measuring_tape.measurement",
                    posA.getX(), posA.getY(), posA.getZ(),
                    clickedPos.getX(), clickedPos.getY(), clickedPos.getZ(),
                    dx, dy, dz, blockDistance, String.format("%.1f", euclideanDistance)),
                true
            );
            player.playSound(SoundEvents.BLOCK_NOTE_BLOCK_PLING, SoundCategory.PLAYERS, 0.8f, 1.5f);

            // Clear for next measurement
            clearMeasurement(stack, player);
        }

        return ActionResult.SUCCESS;
    }

    // ─── NBT Management ─────────────────────────────────────────────────────

    private BlockPos getPosA(ItemStack stack) {
        var nbt = stack.getOrDefault(DataComponentTypes.CUSTOM_DATA, NbtComponent.DEFAULT);
        var copy = nbt.copyNbt();
        if (copy.contains("PosAX") && copy.contains("PosAY") && copy.contains("PosAZ")) {
            return new BlockPos(copy.getInt("PosAX"), copy.getInt("PosAY"), copy.getInt("PosAZ"));
        }
        return null;
    }

    private void setPosA(ItemStack stack, BlockPos pos, PlayerEntity player) {
        var nbt = stack.getOrDefault(DataComponentTypes.CUSTOM_DATA, NbtComponent.DEFAULT);
        var copy = nbt.copyNbt();
        copy.putInt("PosAX", pos.getX());
        copy.putInt("PosAY", pos.getY());
        copy.putInt("PosAZ", pos.getZ());
        stack.set(DataComponentTypes.CUSTOM_DATA, NbtComponent.of(copy));
    }

    private void clearMeasurement(ItemStack stack, PlayerEntity player) {
        var nbt = stack.getOrDefault(DataComponentTypes.CUSTOM_DATA, NbtComponent.DEFAULT);
        var copy = nbt.copyNbt();
        copy.remove("PosAX");
        copy.remove("PosAY");
        copy.remove("PosAZ");
        stack.set(DataComponentTypes.CUSTOM_DATA, NbtComponent.of(copy));
        player.sendMessage(
            Text.translatable("item.buildermc.measuring_tape.reset"),
            true
        );
    }
}
